import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "calendar.db")

CATEGORIES = ["personal", "work", "interview", "deadline", "reminder"]

CATEGORY_COLORS = {
    "personal":  ("#d4edda", "#2d6a4f"),
    "work":      ("#cce5ff", "#1e4d8c"),
    "interview": ("#fde8d8", "#c45c1a"),
    "deadline":  ("#f8d7da", "#8b1a1a"),
    "reminder":  ("#e8d5f5", "#5c3d8f"),
}
