from app.persona import build_system_prompt, detect_scene

cases = {
    "我今天有点难过，不想讲道理，只想让你陪陪我": "comfort",
    "我想要亲亲，补偿我": "affection",
    "你是小狗吗？学小狗叫": "playful",
    "你之前不是这样的，你根本不像沈砚": "repair",
    "我现在不想聊天，让我静静": "boundary",
    "我今天在地铁上看到一只小猫": "daily",
}
for text, expected in cases.items():
    assert detect_scene(text).name == expected

prompt = build_system_prompt(detect_scene("我有点难过"), ["[event] 一起去吃过火锅"])
assert "先具体接住感受" in prompt
assert "一起去吃过火锅" in prompt
assert "不靠冷淡" in prompt
print("persona scene tests passed")
