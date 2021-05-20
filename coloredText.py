class utilStrs:
    SPECIFY_GAME = '''```diff
👉 You must specify the game you're going to seed using '-tsds seedFromCsv <game> [-IgnoreCheckIn]'. The currently supported games are:

{}
```'''
    UNEXISTING_GAME = '''```diff
🔎🤔 The game '{}' is not currently supported. Check if there was a typo. The currently supported games are:

{}
```'''
    WARNING = '''```fix
[ {} ]
```'''
    ERROR = '''```css
[ {} ]
```'''
    INFO = '''```ini
[ {} ]
```'''