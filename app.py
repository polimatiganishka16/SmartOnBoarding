import time, random, os, datetime
from flask import Flask, request, jsonify, render_template, session, redirect
from models import db, User, Activity, ABTest, UserProgress, Notification
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "smart_onboarding_key_2024")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

AVATAR_COLORS = ['#6366f1','#22d3ee','#a78bfa','#f59e0b','#ef4444','#22c55e','#ec4899','#f97316']

STEPS = [
    {"id":1,"title":"Welcome to SmartOnboard","description":"You're about to start a personalized onboarding journey powered by AI. SmartOnboard tracks your behavior and adapts to keep you on the right path.","task":"Read through this introduction carefully, then click Next Step to begin.","tip":"Take your time — the AI scores you on quality of engagement, not speed.","duration":"2 min","type":"info"},
    {"id":2,"title":"Setting Up Your Profile","description":"A complete profile lets our AI tailor its recommendations specifically to you. Personalize your avatar color and make this space your own.","task":"Visit your Profile page and update your avatar color.","tip":"Your avatar color is used across the platform to identify you on the leaderboard.","duration":"3 min","type":"action"},
    {"id":3,"title":"Exploring the Dashboard","description":"Your dashboard is your command center. Monitor your risk score, activity trends, and completion progress — all in real-time.","task":"Navigate to the Dashboard page and review your current analytics.","tip":"Your risk score updates every time you interact with the platform.","duration":"4 min","type":"explore"},
    {"id":4,"title":"AI-Powered Recommendations","description":"Our machine learning engine analyzes your behavioral patterns to deliver targeted, actionable suggestions. The more you interact, the smarter it gets.","task":"Stay active on the platform and check the AI recommendation panel on this page.","tip":"Inactivity for more than 10 seconds is detected and lowers your score temporarily.","duration":"5 min","type":"ai"},
    {"id":5,"title":"Achievements & Leaderboard","description":"Earn points by completing steps, staying active, and updating your profile. Unlock badges and compete with others on the global leaderboard.","task":"Visit the Achievements page to see which badges you can unlock next.","tip":"Completing all steps earns you the exclusive 'Onboarding Master' badge!","duration":"2 min","type":"achievement"}
]
TOTAL_STEPS = len(STEPS)

# ── AI Engine ──
def ai_score(user_id):
    acts = Activity.query.filter_by(user_id=user_id).all()
    score = 0
    for a in acts:
        if a.action == "task_completed": score += 100
        elif a.action == "next": score += 20
        elif a.action == "page_visit": score += 5
        elif a.action == "profile_updated": score += 30
        elif a.action == "login": score += 10
        elif a.action == "inactive": score -= 15
    if score < 0: return "High Risk"
    if score < 80: return "Medium Risk"
    return "Low Risk"

def get_points(user_id):
    acts = Activity.query.filter_by(user_id=user_id).all()
    pts = 0
    for a in acts:
        if a.action == "task_completed": pts += 200
        elif a.action == "next": pts += 30
        elif a.action == "page_visit": pts += 8
        elif a.action == "profile_updated": pts += 60
        elif a.action == "login": pts += 15
        elif a.action == "inactive": pts -= 10
    return max(0, pts)

def get_badges(user_id):
    acts = Activity.query.filter_by(user_id=user_id).all()
    pts = get_points(user_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    step = progress.current_step if progress else 1
    completed = progress.completed if progress else False
    earned = set()
    if len(acts) > 0: earned.add("first_step")
    if pts >= 50: earned.add("beginner")
    if pts >= 300: earned.add("intermediate")
    if pts >= 800: earned.add("pro")
    if step >= 3: earned.add("halfway")
    if completed: earned.add("master")
    all_b = [
        {"id":"first_step","name":"First Action","desc":"Completed your first interaction","icon":"🚀"},
        {"id":"beginner","name":"Beginner","desc":"Earned 50 points","icon":"⭐"},
        {"id":"intermediate","name":"Intermediate","desc":"Earned 300 points","icon":"🌟"},
        {"id":"pro","name":"Pro","desc":"Earned 800 points","icon":"💫"},
        {"id":"halfway","name":"Halfway Hero","desc":"Completed 3 steps","icon":"🎯"},
        {"id":"master","name":"Onboarding Master","desc":"Completed all 5 steps","icon":"🏆"},
        {"id":"streak","name":"On Fire","desc":"Visit for 3 consecutive days","icon":"🔥"},
        {"id":"social","name":"Social Butterfly","desc":"Reach top 10 on leaderboard","icon":"🦋"},
    ]
    for b in all_b:
        b["earned"] = b["id"] in earned
    return all_b

def get_recommendation(user_id):
    r = ai_score(user_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    step = progress.current_step if progress else 1
    if r == "High Risk":
        return {"msg":"You're falling behind! Re-engage with the platform to improve your score.", "type":"warning"}
    if r == "Medium Risk":
        return {"msg":f"Good progress on step {step}! Keep the momentum going to reach Low Risk status.", "type":"info"}
    return {"msg":"Excellent performance! You're excelling at this onboarding process. Keep it up!", "type":"success"}

def add_notif(user_id, message, ntype="info"):
    n = Notification(user_id=user_id, message=message, timestamp=int(time.time()), notif_type=ntype)
    db.session.add(n)
    db.session.commit()

def track(user_id, action):
    a = Activity(user_id=user_id, action=action, timestamp=int(time.time()))
    db.session.add(a)
    try: db.session.commit()
    except: db.session.rollback()

@app.context_processor
def ctx():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        return {'current_user': user}
    return {'current_user': None}

# ── AUTH ──
@app.route('/login')
def login_page():
    if 'user_id' in session: return redirect('/')
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def do_login():
    d = request.json
    u = User.query.filter_by(username=d.get('username','')).first()
    if u and check_password_hash(u.password, d.get('password','')):
        session['user_id'] = u.id
        u.last_active = int(time.time())
        db.session.commit()
        track(u.id, "login")
        return jsonify({"msg":"ok"})
    return jsonify({"msg":"Invalid username or password"}), 401

@app.route('/signup', methods=['POST'])
def do_signup():
    d = request.json
    if not d.get('username') or not d.get('password'):
        return jsonify({"msg":"Username and password required"}), 400
    if User.query.filter_by(username=d['username']).first():
        return jsonify({"msg":"Username already taken"}), 400
    u = User(username=d['username'], password=generate_password_hash(d['password']),
             created_at=int(time.time()), last_active=int(time.time()),
             avatar_color=random.choice(AVATAR_COLORS))
    db.session.add(u)
    db.session.flush()
    db.session.add(UserProgress(user_id=u.id, current_step=1, completed=False))
    db.session.commit()
    add_notif(u.id, "Welcome! Complete your first step to start earning points.", "success")
    return jsonify({"msg":"created"})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

# ── PAGES ──
@app.route('/')
def home():
    if 'user_id' not in session: return redirect('/login')
    uid = session['user_id']
    user = db.session.get(User, uid)
    progress = UserProgress.query.filter_by(user_id=uid).first()
    if not progress:
        progress = UserProgress(user_id=uid, current_step=1, completed=False)
        db.session.add(progress); db.session.commit()
    idx = min(progress.current_step - 1, TOTAL_STEPS - 1)
    track(uid, "page_visit")
    return render_template("index.html",
        step=STEPS[idx], step_num=progress.current_step, total_steps=TOTAL_STEPS,
        progress_pct=int((progress.current_step - 1) / TOTAL_STEPS * 100),
        completed=progress.completed, steps=STEPS)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    track(session['user_id'], "page_visit")
    return render_template("dashboard.html")

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect('/login')
    uid = session['user_id']
    user = db.session.get(User, uid)
    track(uid, "page_visit")
    pts = get_points(uid)
    badges = get_badges(uid)
    earned = sum(1 for b in badges if b["earned"])
    joined = datetime.datetime.fromtimestamp(user.created_at).strftime("%b %d, %Y") if user.created_at else "N/A"
    return render_template("profile.html", user=user, points=pts, earned=earned, total_badges=len(badges), joined=joined, colors=AVATAR_COLORS)

@app.route('/achievements')
def achievements():
    if 'user_id' not in session: return redirect('/login')
    uid = session['user_id']
    track(uid, "page_visit")
    badges = get_badges(uid)
    pts = get_points(uid)
    earned = sum(1 for b in badges if b["earned"])
    return render_template("achievements.html", badges=badges, points=pts, earned=earned, total=len(badges))

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect('/login')
    track(session['user_id'], "page_visit")
    return render_template("leaderboard.html")

# ── API ──
@app.route('/api/track', methods=['POST'])
def api_track():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    track(session['user_id'], request.json.get('action','unknown'))
    return jsonify({"msg":"ok"})

@app.route('/api/next', methods=['POST'])
def api_next():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    uid = session['user_id']
    progress = UserProgress.query.filter_by(user_id=uid).first()
    if not progress:
        progress = UserProgress(user_id=uid, current_step=1)
        db.session.add(progress)
    if progress.current_step < TOTAL_STEPS:
        progress.current_step += 1
        track(uid, "next")
        db.session.commit()
        return jsonify({"step": progress.current_step, "completed": False})
    else:
        if not progress.completed:
            progress.completed = True
            progress.completed_at = int(time.time())
            track(uid, "task_completed")
            db.session.commit()
            add_notif(uid, "Congratulations! You've completed all onboarding steps and earned the Onboarding Master badge!", "success")
        return jsonify({"step": progress.current_step, "completed": True})

@app.route('/api/prev', methods=['POST'])
def api_prev():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    uid = session['user_id']
    progress = UserProgress.query.filter_by(user_id=uid).first()
    if progress and progress.current_step > 1:
        progress.current_step -= 1
        db.session.commit()
    return jsonify({"step": progress.current_step if progress else 1})

@app.route('/api/summary')
def api_summary():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    uid = session['user_id']
    acts = Activity.query.filter_by(user_id=uid).all()
    inactive = sum(1 for a in acts if a.action == "inactive")
    progress = UserProgress.query.filter_by(user_id=uid).first()
    step = progress.current_step if progress else 1
    return jsonify({
        "actions": len(acts), "time": len(acts) * 2, "inactive": inactive,
        "risk": ai_score(uid), "points": get_points(uid),
        "step": step, "total_steps": TOTAL_STEPS,
        "progress_pct": int((step - 1) / TOTAL_STEPS * 100),
        "completed": progress.completed if progress else False
    })

@app.route('/api/recommend')
def api_recommend():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    return jsonify(get_recommendation(session['user_id']))

@app.route('/api/ab-test')
def api_ab():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    uid = session['user_id']
    ex = ABTest.query.filter_by(user_id=uid).first()
    if ex: return jsonify({"variant": ex.variant})
    v = random.choice(["A","B"])
    db.session.add(ABTest(user_id=uid, variant=v)); db.session.commit()
    return jsonify({"variant": v})

@app.route('/api/achievements')
def api_achievements():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    uid = session['user_id']
    return jsonify({"points": get_points(uid), "badges": get_badges(uid)})

@app.route('/api/leaderboard')
def api_leaderboard():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    users = User.query.all()
    board = []
    for u in users:
        pts = get_points(u.id)
        progress = UserProgress.query.filter_by(user_id=u.id).first()
        step = progress.current_step if progress else 1
        board.append({"id":u.id,"username":u.username,"points":pts,"step":step,
                      "avatar_color":u.avatar_color or '#6366f1',"is_current":u.id==session['user_id']})
    board.sort(key=lambda x: x["points"], reverse=True)
    for i, b in enumerate(board): b["rank"] = i + 1
    return jsonify(board)

@app.route('/api/notifications')
def api_notifs():
    if 'user_id' not in session: return jsonify([])
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.timestamp.desc()).limit(10).all()
    return jsonify([{"id":n.id,"message":n.message,"type":n.notif_type,"read":n.read,"timestamp":n.timestamp} for n in notifs])

@app.route('/api/notifications/read', methods=['POST'])
def api_notifs_read():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    Notification.query.filter_by(user_id=session['user_id']).update({"read":True})
    db.session.commit()
    return jsonify({"msg":"ok"})

@app.route('/api/profile/update', methods=['POST'])
def api_profile_update():
    if 'user_id' not in session: return jsonify({"msg":"Unauthorized"}), 401
    d = request.json
    user = db.session.get(User, session['user_id'])
    if d.get('avatar_color'): user.avatar_color = d['avatar_color']
    db.session.commit()
    track(user.id, "profile_updated")
    return jsonify({"msg":"updated"})

@app.route('/api/chart/activity')
def api_chart_activity():
    if 'user_id' not in session: return jsonify([])
    uid = session['user_id']
    acts = Activity.query.filter_by(user_id=uid).all()
    now = int(time.time())
    result = []
    for i in range(6, -1, -1):
        ds = now - (i+1)*86400; de = now - i*86400
        count = sum(1 for a in acts if ds <= a.timestamp < de)
        label = datetime.datetime.fromtimestamp(ds).strftime("%a")
        result.append({"day": label, "count": count})
    return jsonify(result)

@app.route('/api/chart/actions')
def api_chart_actions():
    if 'user_id' not in session: return jsonify({})
    acts = Activity.query.filter_by(user_id=session['user_id']).all()
    counts = {}
    for a in acts:
        counts[a.action] = counts.get(a.action, 0) + 1
    return jsonify(counts)

if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
