from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Tournament, Team, Player, Match, MatchUpdate, MatchStats, PlayerStats, PlayerMatchPerformance
from forms import TournamentForm, TeamForm, PlayerForm, MatchForm, ScoreForm
from datetime import datetime, timedelta
import itertools
import random

@app.route('/')
def index():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).limit(5).all()
    recent_matches = Match.query.filter_by(status='completed').order_by(Match.match_date.desc()).limit(5).all()
    return render_template('index.html', tournaments=tournaments, recent_matches=recent_matches)

# Tournament routes
@app.route('/tournaments')
def tournaments():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('tournaments/list.html', tournaments=tournaments)

@app.route('/tournaments/create', methods=['GET', 'POST'])
def create_tournament():
    form = TournamentForm()
    if form.validate_on_submit():
        tournament = Tournament(
            name=form.name.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            max_teams=form.max_teams.data
        )
        db.session.add(tournament)
        db.session.commit()
        flash(f'Tournament "{tournament.name}" created successfully!', 'success')
        return redirect(url_for('tournaments'))
    return render_template('tournaments/create.html', form=form)

@app.route('/tournaments/<int:id>')
def tournament_detail(id):
    tournament = Tournament.query.get_or_404(id)
    teams = Team.query.filter_by(tournament_id=id).all()
    matches = Match.query.filter_by(tournament_id=id).order_by(Match.match_date).all()
    
    # Calculate standings
    standings = []
    for team in teams:
        stats = team.get_stats()
        standings.append({
            'team': team,
            'stats': stats
        })
    
    # Sort standings by points, then goal difference, then goals for
    standings.sort(key=lambda x: (x['stats']['points'], x['stats']['goal_difference'], x['stats']['goals_for']), reverse=True)
    
    return render_template('tournaments/detail.html', tournament=tournament, teams=teams, matches=matches, standings=standings)

@app.route('/tournaments/<int:id>/generate_fixtures', methods=['POST'])
def generate_fixtures(id):
    tournament = Tournament.query.get_or_404(id)
    teams = Team.query.filter_by(tournament_id=id).all()
    
    if len(teams) < 2:
        flash('Need at least 2 teams to generate fixtures!', 'error')
        return redirect(url_for('tournament_detail', id=id))
    
    # Delete existing matches
    Match.query.filter_by(tournament_id=id).delete()
    
    # Generate round-robin fixtures
    team_combinations = list(itertools.combinations(teams, 2))
    start_date = tournament.start_date
    
    for i, (home_team, away_team) in enumerate(team_combinations):
        match_date = start_date + timedelta(days=i * 3)  # Matches every 3 days
        match = Match(
            tournament_id=id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=match_date,
            round_number=1
        )
        db.session.add(match)
    
    tournament.status = 'active'
    db.session.commit()
    flash('Fixtures generated successfully!', 'success')
    return redirect(url_for('tournament_detail', id=id))

# Team routes
@app.route('/teams')
def teams():
    teams = Team.query.order_by(Team.name).all()
    return render_template('teams/list.html', teams=teams)

@app.route('/tournaments/<int:tournament_id>/teams/create', methods=['GET', 'POST'])
def create_team(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    form = TeamForm()
    
    if form.validate_on_submit():
        # Check if tournament is full
        team_count = Team.query.filter_by(tournament_id=tournament_id).count()
        if team_count >= tournament.max_teams:
            flash('Tournament is full!', 'error')
            return redirect(url_for('tournament_detail', id=tournament_id))
        
        team = Team(
            name=form.name.data,
            city=form.city.data,
            founded_year=form.founded_year.data,
            coach=form.coach.data,
            tournament_id=tournament_id
        )
        db.session.add(team)
        db.session.commit()
        flash(f'Team "{team.name}" registered successfully!', 'success')
        return redirect(url_for('tournament_detail', id=tournament_id))
    
    return render_template('teams/create.html', form=form, tournament=tournament)

@app.route('/teams/<int:id>')
def team_detail(id):
    team = Team.query.get_or_404(id)
    players = Player.query.filter_by(team_id=id).order_by(Player.jersey_number).all()
    stats = team.get_stats()
    
    # Get player stats for the team
    players_with_stats = []
    for player in players:
        player_stats = player.get_stats()
        players_with_stats.append({
            'player': player,
            'stats': player_stats
        })
    
    return render_template('teams/detail.html', team=team, players=players_with_stats, stats=stats)

# Player routes
@app.route('/players')
def players():
    players = Player.query.join(Team).order_by(Team.name, Player.jersey_number).all()
    return render_template('players/list.html', players=players)

@app.route('/teams/<int:team_id>/players/create', methods=['GET', 'POST'])
def create_player(team_id):
    team = Team.query.get_or_404(team_id)
    form = PlayerForm()
    
    if form.validate_on_submit():
        # Check if jersey number is already taken
        existing_player = Player.query.filter_by(team_id=team_id, jersey_number=form.jersey_number.data).first()
        if existing_player:
            flash('Jersey number is already taken!', 'error')
            return render_template('players/create.html', form=form, team=team)
        
        player = Player(
            name=form.name.data,
            position=form.position.data,
            jersey_number=form.jersey_number.data,
            age=form.age.data,
            nationality=form.nationality.data,
            team_id=team_id
        )
        db.session.add(player)
        db.session.commit()
        flash(f'Player "{player.name}" added successfully!', 'success')
        return redirect(url_for('team_detail', id=team_id))
    
    return render_template('players/create.html', form=form, team=team)

# Match routes
@app.route('/matches')
def matches():
    matches = Match.query.order_by(Match.match_date.desc()).all()
    return render_template('matches/list.html', matches=matches)

@app.route('/matches/<int:id>/update_score', methods=['GET', 'POST'])
def update_score(id):
    match = Match.query.get_or_404(id)
    form = ScoreForm()
    
    if request.method == 'GET':
        form.home_score.data = match.home_score
        form.away_score.data = match.away_score
    
    if form.validate_on_submit():
        match.home_score = form.home_score.data
        match.away_score = form.away_score.data
        match.status = 'completed'
        db.session.commit()
        flash('Match score updated successfully!', 'success')
        return redirect(url_for('matches'))
    
    return render_template('matches/update_score.html', form=form, match=match)

@app.route('/tournaments/<int:id>/standings')
def standings(id):
    tournament = Tournament.query.get_or_404(id)
    teams = Team.query.filter_by(tournament_id=id).all()
    
    standings = []
    for team in teams:
        stats = team.get_stats()
        standings.append({
            'team': team,
            'stats': stats
        })
    
    # Sort standings by points, then goal difference, then goals for
    standings.sort(key=lambda x: (x['stats']['points'], x['stats']['goal_difference'], x['stats']['goals_for']), reverse=True)
    
    return render_template('standings.html', tournament=tournament, standings=standings)

# Live Match Routes
@app.route('/matches/<int:id>/live')
def live_match(id):
    match = Match.query.get_or_404(id)
    
    # Create match stats if they don't exist
    if not match.stats_detail:
        stats = MatchStats(match_id=id)
        db.session.add(stats)
        db.session.commit()
    
    return render_template('matches/live.html', match=match)

# API Routes for Live Updates
@app.route('/api/matches/<int:id>/live')
def api_live_match_data(id):
    match = Match.query.get_or_404(id)
    
    # Get recent updates (last 10)
    recent_updates = MatchUpdate.query.filter_by(match_id=id)\
                                    .order_by(MatchUpdate.timestamp.desc())\
                                    .limit(10).all()
    
    # Get match stats
    stats = match.stats_detail
    
    response_data = {
        'home_score': match.home_score,
        'away_score': match.away_score,
        'status': match.status,
        'updates': [update.to_dict() for update in recent_updates],
        'stats': stats.to_dict() if stats else None
    }
    
    return jsonify(response_data)

@app.route('/api/matches/<int:id>/score', methods=['POST'])
def api_update_score(id):
    match = Match.query.get_or_404(id)
    data = request.get_json()
    
    team = data.get('team')  # 'home' or 'away'
    
    if team == 'home':
        match.home_score += 1
        team_obj = Team.query.get(match.home_team_id)
    elif team == 'away':
        match.away_score += 1
        team_obj = Team.query.get(match.away_team_id)
    else:
        return jsonify({'error': 'Invalid team'}), 400
    
    # Create match update
    update = MatchUpdate(
        match_id=id,
        minute=random.randint(1, 90),
        update_type='goal',
        team_id=team_obj.id,
        description=f'⚽ BUT ! {team_obj.name} marque !'
    )
    
    # Update match stats
    if not match.stats_detail:
        stats = MatchStats(match_id=id)
        db.session.add(stats)
    else:
        stats = match.stats_detail
    
    # Simulate some stats updates
    if team == 'home':
        stats.home_shots += random.randint(1, 3)
        stats.home_shots_on_target += 1
    else:
        stats.away_shots += random.randint(1, 3)
        stats.away_shots_on_target += 1
    
    # Random possession adjustment
    possession_change = random.randint(-5, 5)
    if team == 'home':
        stats.home_possession = min(100, max(0, stats.home_possession + possession_change))
        stats.away_possession = 100 - stats.home_possession
    else:
        stats.away_possession = min(100, max(0, stats.away_possession + possession_change))
        stats.home_possession = 100 - stats.away_possession
    
    db.session.add(update)
    db.session.commit()
    
    return jsonify({
        'home_score': match.home_score,
        'away_score': match.away_score,
        'status': match.status,
        'stats': stats.to_dict(),
        'updates': [update.to_dict()]
    })

@app.route('/api/matches/<int:id>/start', methods=['POST'])
def api_start_match(id):
    match = Match.query.get_or_404(id)
    match.status = 'in_progress'
    
    # Create kick-off update
    update = MatchUpdate(
        match_id=id,
        minute=0,
        update_type='kickoff',
        description='🟢 Le match commence !'
    )
    
    db.session.add(update)
    db.session.commit()
    
    return jsonify({'status': 'success', 'match_status': match.status})

@app.route('/api/matches/<int:id>/end', methods=['POST'])
def api_end_match(id):
    match = Match.query.get_or_404(id)
    match.status = 'completed'
    
    # Create final whistle update
    update = MatchUpdate(
        match_id=id,
        minute=90,
        update_type='final_whistle',
        description='🔴 Fin du match !'
    )
    
    db.session.add(update)
    db.session.commit()
    
    return jsonify({'status': 'success', 'match_status': match.status})

# Player Statistics Routes
@app.route('/players/<int:id>')
def player_detail(id):
    player = Player.query.get_or_404(id)
    stats = player.get_stats()
    
    # Get recent match performances
    recent_performances = PlayerMatchPerformance.query.filter_by(player_id=id)\
                                                    .order_by(PlayerMatchPerformance.created_at.desc())\
                                                    .limit(10).all()
    
    return render_template('players/detail.html', player=player, stats=stats, recent_performances=recent_performances)

@app.route('/players/stats')
def player_stats_leaderboard():
    # Get top scorers
    top_scorers = db.session.query(Player, PlayerStats)\
                           .join(PlayerStats, Player.id == PlayerStats.player_id)\
                           .order_by(PlayerStats.goals.desc())\
                           .limit(10).all()
    
    # Get top assists
    top_assists = db.session.query(Player, PlayerStats)\
                           .join(PlayerStats, Player.id == PlayerStats.player_id)\
                           .order_by(PlayerStats.assists.desc())\
                           .limit(10).all()
    
    # Get most cards
    most_cards = db.session.query(Player, PlayerStats)\
                          .join(PlayerStats, Player.id == PlayerStats.player_id)\
                          .order_by((PlayerStats.yellow_cards + PlayerStats.red_cards).desc())\
                          .limit(10).all()
    
    return render_template('players/stats.html', 
                         top_scorers=top_scorers, 
                         top_assists=top_assists, 
                         most_cards=most_cards)
