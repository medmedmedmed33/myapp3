from extensions import db
from datetime import datetime
from sqlalchemy import func, Table, Column, Integer, ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Association table for many-to-many relationship between Match and Referee
match_referees = Table('match_referees',
    db.Model.metadata,
    Column('match_id', Integer, ForeignKey('match.id'), primary_key=True),
    Column('referee_id', Integer, ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    
    # Relations polymorphiques
    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': role
    }
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Admin(User):
    __tablename__ = 'admin'
    __mapper_args__ = {
        'polymorphic_identity': 'admin',
    }
    
    def can_manage_tournaments(self):
        return True
    
    def can_manage_teams(self):
        return True

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    city = db.Column(db.String(80))
    founded_year = db.Column(db.Integer)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add a foreign key for the coach
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Coach can be optional initially
    
    # Relationships
    players = db.relationship('Player', backref='team', lazy=True, cascade='all, delete-orphan')
    home_matches = db.relationship('Match', foreign_keys='Match.home_team_id', backref='home_team', lazy=True)
    away_matches = db.relationship('Match', foreign_keys='Match.away_team_id', backref='away_team', lazy=True)
    
    # Define the relationship to the Coach (User) model
    coach = db.relationship('Coach', foreign_keys=[coach_id], backref=db.backref('team', uselist=False), uselist=False)

    def __repr__(self):
        return f'<Team {self.name}>'
    
    def get_stats(self):
        """Calculate team statistics"""
        stats = {
            'played': 0,
            'won': 0,
            'drawn': 0,
            'lost': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0
        }
        
        # Get all matches for this team
        matches = Match.query.filter(
            db.or_(Match.home_team_id == self.id, Match.away_team_id == self.id),
            Match.status == 'completed'
        ).all()
        
        for match in matches:
            if match.home_team_id == self.id:
                goals_for = match.home_score
                goals_against = match.away_score
            else:
                goals_for = match.away_score
                goals_against = match.home_score
            
            stats['played'] += 1
            stats['goals_for'] += goals_for
            stats['goals_against'] += goals_against
            
            if goals_for > goals_against:
                stats['won'] += 1
                stats['points'] += 3
            elif goals_for == goals_against:
                stats['drawn'] += 1
                stats['points'] += 1
            else:
                stats['lost'] += 1
        
        stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
        return stats

    def get_available_players(self):
        """Retourne la liste des joueurs disponibles pour le prochain match"""
        return Player.query.filter_by(team_id=self.id, is_available=True).all()
    
    def select_players_for_match(self, match_id, player_ids):
        """Sélectionne les joueurs pour un match spécifique"""
        # Vérifier que tous les joueurs appartiennent à l'équipe
        players = Player.query.filter(
            Player.id.in_(player_ids),
            Player.team_id == self.id
        ).all()
        
        # Supprimer les sélections précédentes pour ce match et cette équipe
        PlayerMatchPerformance.query.filter(
            PlayerMatchPerformance.match_id == match_id,
            PlayerMatchPerformance.player_id.in_([p.id for p in self.players])
        ).delete(synchronize_session=False)

        # Créer les performances des joueurs pour le match
        for player in players:
            # S'assurer qu'une performance n'existe pas déjà pour ce joueur et ce match
            performance = PlayerMatchPerformance.query.filter_by(
                player_id=player.id,
                match_id=match_id
            ).first()
            
            if not performance:
                performance = PlayerMatchPerformance(
                    player_id=player.id,
                    match_id=match_id,
                    is_selected=True # Marquer comme sélectionné
                )
                db.session.add(performance)
            else:
                # Mettre à jour si déjà existant
                performance.is_selected = True
        
        db.session.commit()
        return players

class Coach(User):
    __tablename__ = 'coach'
    __mapper_args__ = {
        'polymorphic_identity': 'coach',
    }
    
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    
    def can_manage_team(self, team_id):
        return self.team_id == team_id
    
    def can_select_players(self, team_id):
        return self.team_id == team_id

class Referee(User):
    __tablename__ = 'referee'
    __mapper_args__ = {
        'polymorphic_identity': 'referee',
    }
    
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    nationality = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Many-to-many relationship with Match
    officiated_matches = db.relationship('Match', secondary=match_referees, backref=db.backref('referees', lazy='dynamic'))

    def __repr__(self):
        return f'<Referee {self.first_name} {self.last_name}>'

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    max_teams = db.Column(db.Integer, default=16)
    status = db.Column(db.String(50), default='registration')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teams = db.relationship('Team', backref='tournament', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='tournament', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tournament {self.name}>'

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    position = db.Column(db.String(20))  # goalkeeper, defender, midfielder, forward
    jersey_number = db.Column(db.Integer)
    age = db.Column(db.Integer)
    nationality = db.Column(db.String(50))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)  # Si le joueur est disponible pour jouer

    def __repr__(self):
        return f'<Player {self.name}>'
    
    def get_stats(self):
        """Calculate player statistics"""
        stats = PlayerStats.query.filter_by(player_id=self.id).first()
        if not stats:
            stats = PlayerStats(player_id=self.id)
            db.session.add(stats)
            db.session.commit()
        return stats

    def toggle_availability(self):
        """Change la disponibilité du joueur"""
        self.is_available = not self.is_available
        db.session.commit()
        return self.is_available

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    match_date = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(100))
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='scheduled')
    round_number = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Match {self.home_team.name} vs {self.away_team.name} on {self.match_date}>'
    
    @property
    def result_string(self):
        if self.status == 'completed':
            return f"{self.home_score} - {self.away_score}"
        return "vs"

class MatchUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    minute = db.Column(db.Integer)  # Match minute
    update_type = db.Column(db.String(20))  # goal, card, substitution, etc.
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    match = db.relationship('Match', backref='updates')
    team = db.relationship('Team')
    player = db.relationship('Player')
    
    def to_dict(self):
        return {
            'id': self.id,
            'minute': self.minute,
            'type': self.update_type,
            'team': self.team.name if self.team else None,
            'player': self.player.name if self.player else None,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'text': self.description,
            'time': self.timestamp.strftime('%H:%M')
        }

class MatchStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    home_possession = db.Column(db.Integer, default=50)
    away_possession = db.Column(db.Integer, default=50)
    home_shots = db.Column(db.Integer, default=0)
    away_shots = db.Column(db.Integer, default=0)
    home_shots_on_target = db.Column(db.Integer, default=0)
    away_shots_on_target = db.Column(db.Integer, default=0)
    home_corners = db.Column(db.Integer, default=0)
    away_corners = db.Column(db.Integer, default=0)
    home_fouls = db.Column(db.Integer, default=0)
    away_fouls = db.Column(db.Integer, default=0)
    home_yellow_cards = db.Column(db.Integer, default=0)
    away_yellow_cards = db.Column(db.Integer, default=0)
    home_red_cards = db.Column(db.Integer, default=0)
    away_red_cards = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    match = db.relationship('Match', backref='stats_detail', uselist=False)
    
    def to_dict(self):
        return {
            'possession': {
                'home': self.home_possession,
                'away': self.away_possession
            },
            'shots': {
                'home': self.home_shots,
                'away': self.away_shots
            },
            'shots_on_target': {
                'home': self.home_shots_on_target,
                'away': self.away_shots_on_target
            },
            'corners': {
                'home': self.home_corners,
                'away': self.away_corners
            },
            'fouls': {
                'home': self.home_fouls,
                'away': self.away_fouls
            },
            'cards': {
                'home_yellow': self.home_yellow_cards,
                'away_yellow': self.away_yellow_cards,
                'home_red': self.home_red_cards,
                'away_red': self.away_red_cards
            }
        }

class PlayerStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    minutes_played = db.Column(db.Integer, default=0)
    shots = db.Column(db.Integer, default=0)
    shots_on_target = db.Column(db.Integer, default=0)
    passes = db.Column(db.Integer, default=0)
    pass_accuracy = db.Column(db.Float, default=0.0)
    tackles = db.Column(db.Integer, default=0)
    interceptions = db.Column(db.Integer, default=0)
    clean_sheets = db.Column(db.Integer, default=0)  # For goalkeepers
    saves = db.Column(db.Integer, default=0)  # For goalkeepers
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    player = db.relationship('Player', backref='stats_record', uselist=False)
    
    def to_dict(self):
        return {
            'goals': self.goals,
            'assists': self.assists,
            'yellow_cards': self.yellow_cards,
            'red_cards': self.red_cards,
            'matches_played': self.matches_played,
            'minutes_played': self.minutes_played,
            'shots': self.shots,
            'shots_on_target': self.shots_on_target,
            'shooting_accuracy': round((self.shots_on_target / self.shots * 100) if self.shots > 0 else 0, 1),
            'passes': self.passes,
            'pass_accuracy': self.pass_accuracy,
            'tackles': self.tackles,
            'interceptions': self.interceptions,
            'clean_sheets': self.clean_sheets,
            'saves': self.saves,
            'goals_per_match': round(self.goals / self.matches_played, 2) if self.matches_played > 0 else 0,
            'assists_per_match': round(self.assists / self.matches_played, 2) if self.matches_played > 0 else 0
        }

class PlayerMatchPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)
    minutes_played = db.Column(db.Integer, default=0)
    shots = db.Column(db.Integer, default=0)
    shots_on_target = db.Column(db.Integer, default=0)
    passes = db.Column(db.Integer, default=0)
    passes_completed = db.Column(db.Integer, default=0)
    tackles = db.Column(db.Integer, default=0)
    interceptions = db.Column(db.Integer, default=0)
    saves = db.Column(db.Integer, default=0)  # For goalkeepers
    rating = db.Column(db.Float, default=0.0)  # Match rating out of 10
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_selected = db.Column(db.Boolean, default=False)  # Si le joueur est sélectionné pour le match
    is_playing = db.Column(db.Boolean, default=False)   # Si le joueur est sur le terrain
    
    # Relationships
    player = db.relationship('Player', backref='match_performances')
    match = db.relationship('Match', backref='player_performances')
    
    def to_dict(self):
        return {
            'player_name': self.player.name,
            'match_info': f"{self.match.home_team.name} vs {self.match.away_team.name}",
            'goals': self.goals,
            'assists': self.assists,
            'yellow_cards': self.yellow_cards,
            'red_cards': self.red_cards,
            'minutes_played': self.minutes_played,
            'shots': self.shots,
            'shots_on_target': self.shots_on_target,
            'passes': self.passes,
            'passes_completed': self.passes_completed,
            'pass_accuracy': round((self.passes_completed / self.passes * 100) if self.passes > 0 else 0, 1),
            'tackles': self.tackles,
            'interceptions': self.interceptions,
            'saves': self.saves,
            'rating': self.rating
        }
