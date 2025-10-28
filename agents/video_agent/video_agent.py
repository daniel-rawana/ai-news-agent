from gtts import gTTS


with open("Story.txt" , "r") as file:
    text = file.read()

tts = gTTS(text=text, lang='en')

tts.save('Story.mp3')
