from ai_engine.utils import load_md

# These are mock versions of internal backend sevrices we would call

AVAILABLE_INTERNSHIPS = ["Digital Marketing", "Data Analytics", "Cyber Security", "Product Design"]
def get_user_info():
    user = {
        "name": "Grace",
        "internship": "Digital Marketing",
        "streak": 7,
        "level": "Beginner",
        "current_task": "Audience Research",
        "current_week": 1,
    }

    return (
        f"Name: {user['name']}, "
        f"Internship: {user['internship']}, "
        f"Streak: {user['streak']} days, "
        f"Level: {user['level']} "
        f"CurrentTask: {user['current_task']}"
        f"CurrentWeek: {user['current_week']}"
    )

def get_available_internships():
    return AVAILABLE_INTERNSHIPS

# This would take the user's id or something as a param
def get_chat_history():
    return """
    Assume we have been talking previously and this is the previous chat history
"""

def get_task():
    week_task = load_md("../tasks/digital_marketing/1")
    return week_task