from app import app
from extensions import db
from models import User, Admin, Coach, Referee, Tournament, Team, Player, Match
from werkzeug.security import generate_password_hash
from datetime import datetime, date
import random
import string

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

def seed_users():
    print("Seeding users...")
    # Check if admin already exists to avoid creating duplicates
    if not Admin.query.first():
        admin_user = Admin(
            username='admin',
            email='admin@example.com',
            first_name='Super',
            last_name='Admin',
            role='admin'
        )
        admin_user.set_password('adminpassword') # TODO: Use a stronger password in production
        db.session.add(admin_user)
        print(" - Created Admin user")

    # Create some coaches
    coaches_data = [
        {'first_name': 'Walid', 'last_name': 'Regragui', 'email': 'walid.regragui@example.com'},
        {'first_name': 'Jamal', 'last_name': 'Sellami', 'email': 'jamal.sellami@example.com'},
        {'first_name': 'Faouzi', 'last_name': 'Benzarti', 'email': 'faouzi.benzarti@example.com'},
    ]

    for coach_data in coaches_data:
        if not User.query.filter_by(email=coach_data['email']).first():
            username_base = f"{coach_data['first_name'][0]}{coach_data['last_name']}".lower()
            username = f"{username_base}_{random.choices(string.digits, k=3)[0]}" # Simple unique username
            password = generate_random_password()
            coach_user = Coach(
                username=username,
                email=coach_data['email'],
                first_name=coach_data['first_name'],
                last_name=coach_data['last_name'],
                role='coach'
            )
            coach_user.set_password(password)
            db.session.add(coach_user)
            print(f" - Created Coach: {coach_user.username} with password {password}")

    # Create some referees
    referees_data = [
        {'first_name': 'Redouane', 'last_name': 'Jiyed', 'email': 'redouane.jiyed@example.com', 'nationality': 'Moroccan'},
        {'first_name': 'Samir', 'last_name': 'Guezzaz', 'email': 'samir.guezzaz@example.com', 'nationality': 'Moroccan'},
    ]

    for referee_data in referees_data:
        if not User.query.filter_by(email=referee_data['email']).first():
             username_base = f"{referee_data['first_name'][0]}{referee_data['last_name']}".lower()
             username = f"{username_base}_{random.choices(string.digits, k=3)[0]}" # Simple unique username
             password = generate_random_password()
             referee_user = Referee(
                 username=username,
                 email=referee_data['email'],
                 first_name=referee_data['first_name'],
                 last_name=referee_data['last_name'],
                 role='referee',
                 nationality=referee_data['nationality']
             )
             referee_user.set_password(password)
             db.session.add(referee_user)
             print(f" - Created Referee: {referee_user.username} with password {password}")

    db.session.commit()
    print("Users seeding complete.")

def seed_tournaments():
    print("Seeding tournaments...")
    if not Tournament.query.first():
        tournament = Tournament(
            name='Botola Pro 1',
            description='Top tier Moroccan football league',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 15),
            max_teams=16,
            status='registration'
        )
        db.session.add(tournament)
        db.session.commit()
        print(" - Created Tournament: Botola Pro 1")
    else:
        tournament = Tournament.query.first()
        print(f"Tournament '{tournament.name}' already exists.")

    print("Tournaments seeding complete.")
    return tournament

def seed_teams(tournament):
    print("Seeding teams...")
    teams_data = [
        {'name': 'Raja Club Athletic', 'city': 'Casablanca', 'founded_year': 1949},
        {'name': 'Wydad Athletic Club', 'city': 'Casablanca', 'founded_year': 1937},
        {'name': 'AS FAR', 'city': 'Rabat', 'founded_year': 1958},
        {'name': 'RS Berkane', 'city': 'Berkane', 'founded_year': 1958},
        {'name': 'FUS Rabat', 'city': 'Rabat', 'founded_year': 1946},
    ]

    coaches = Coach.query.all()
    assigned_coaches = set()

    for team_data in teams_data:
        team = Team.query.filter_by(name=team_data['name'], tournament_id=tournament.id).first()
        if not team:
            team = Team(
                name=team_data['name'],
                city=team_data['city'],
                founded_year=team_data['founded_year'],
                tournament_id=tournament.id
            )
            # Assign a random available coach
            available_coaches = [c for c in coaches if c.id not in assigned_coaches]
            if available_coaches:
                assigned_coach = random.choice(available_coaches)
                team.coach = assigned_coach
                assigned_coaches.add(assigned_coach.id)
                print(f" - Assigned coach {assigned_coach.username} to {team.name}")
            else:
                print(f" - No available coaches to assign to {team.name}")

            db.session.add(team)
            print(f" - Created Team: {team.name}")

    db.session.commit()
    print("Teams seeding complete.")

def seed_players(teams):
    print("Seeding players...")
    players_data = {
        'Raja Club Athletic': ['Anas Zniti', 'Abdeljalil Jbira', 'Mohsine Moutouali', 'Zakaria Hadraf'],
        'Wydad Athletic Club': ['Ahmed Reda Tagnaouti', 'Yahya Attiat Allah', 'Ayman El Hassouni', 'Guy Mbenza'],
        'AS FAR': ['Ayoub El Khaliqi', 'Mohamed Bourouis', 'Hamid Ahadad'],
        'RS Berkane': ['Hamza Akandouch', 'Charki Bahri'],
        'FUS Rabat': ['Mehdi Bellaroussi', 'El Mehdi Karnass'],
    }

    for team in teams:
        if team.name in players_data:
            for player_name in players_data[team.name]:
                if not Player.query.filter_by(name=player_name, team_id=team.id).first():
                    player = Player(
                        name=player_name,
                        position='unknown', # Can be updated later
                        jersey_number=random.randint(1, 99),
                        age=random.randint(18, 35),
                        nationality='Moroccan',
                        team_id=team.id
                    )
                    db.session.add(player)
                    print(f" - Added player {player.name} to {team.name}")
    db.session.commit()
    print("Players seeding complete.")

def seed_matches(tournament, teams):
    print("Seeding matches...")
    # Create a few example matches for the tournament
    if len(teams) >= 2 and len(tournament.matches) == 0:
        # Simple example: first two teams play each other
        match1 = Match(
            tournament_id=tournament.id,
            home_team_id=teams[0].id,
            away_team_id=teams[1].id,
            match_date=datetime(2024, 9, 15, 18, 0, 0),
            venue='Stade Mohammed V',
            round_number=1
        )
        db.session.add(match1)
        print(f" - Created match: {teams[0].name} vs {teams[1].name}")

    db.session.commit()
    print("Matches seeding complete.")

if __name__ == '__main__':
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()

        seed_users()
        tournament = seed_tournaments()
        # Only seed teams and players if a tournament was created or found
        if tournament:
            teams = Team.query.filter_by(tournament_id=tournament.id).all()
            # Only seed teams if there are less than max_teams in the tournament
            if len(teams) < tournament.max_teams:
                 seed_teams(tournament)
                 teams = Team.query.filter_by(tournament_id=tournament.id).all() # Refresh teams list

            seed_players(teams)
            seed_matches(tournament, teams)

        print("Database seeding complete.") 