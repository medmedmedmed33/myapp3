from app import db
from datetime import datetime
from sqlalchemy import func

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