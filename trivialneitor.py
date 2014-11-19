from willie.module import commands, interval, rule
import willie.bot
import random
from functools import wraps
import threading
import os.path

# https://docs.python.org/2/library/threading.html
# http://stackoverflow.com/questions/9812344/cancellable-threading-timer-in-python
# http://stackoverflow.com/questions/16578652/threading-timer
# http://stackoverflow.com/questions/12435211/python-threading-timer-repeat-function-every-n-seconds
# <Zokormazo> nu_kru, hay un descriptor, @interval(5)
# <Zokormazo> Ejecuta la fincion cada 5 segundos
# <Zokormazo> Puedes usarlo de main loop para la logica
# <NoPlanB> Buenas vivi666_!
# <Zokormazo> Mira en rss.py por ejemplo
# https://github.com/inspectorvector/avalon/blob/master/avalon.py
# http://stackoverflow.com/questions/11488877/periodically-execute-function-in-thread-in-real-time-every-n-seconds
home = os.path.expanduser("~")
_file_ = os.path.join(home,'proyectos/trivialneitor/questions/[ES]questions')
INTERVAL = 5
list_questions = []
running_game = False
answerd = None
lock =  None
score = None

def check_running_game(f):  # pragma: no cover
    """Checks if the game is running or not"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if running_game:
            return f(*args, **kwargs)
        else:
            return None
    return decorated_function

class Answerd:
    def __init__(self, answerd):
        self.answerd = answerd
        self.mask = [False]*len(answerd)
        self.number_letters_show = 0
        for i,x in enumerate(answerd):
            if x == ' ':
                self.mask[i]=True

    def show_more_letters(self):
        # print self.mask.count(True), len(self.answerd)
        if self.mask.count(True)<len(self.answerd):
            i = random.randrange(len(self.answerd))
            while self.mask[i]==True:
                i = random.randrange(len(self.answerd))
            self.mask[i]=True
            self.number_letters_show = self.number_letters_show + 1
        return self.string_mask()

    def string_mask(self):
        aux = ""
        for i,x in enumerate(self.mask):
            if x:
                aux = aux + self.answerd[i] + " "
            else : 
                aux = aux + "_ "
        return aux
        
    def stop(self):
        # race condition
        if ((self.number_letters_show*2>=len(self.answerd))):
            return True
        else:
            return False

class Question:
    def __init__(self, list):
        self.theme_autor = list[0]
        self.question = list[1]
        self.answerd = list[2].replace('\n','')

def setup(bot):
    global running_game
    running_game = False
    global lock
    lock = threading.Lock()
    global score
    score ={}
    with open(_file_, 'r') as f:
        for line in f:
            l = line.split('*')
            if len(l)==3:
                list_questions.append(Question(l))


@commands('trivial_start')
def trivial(bot, trigger):
    global running_game
    if running_game == False:
        running_game = True
        send_question(bot)
    else :
        bot.say("juego ya ha comenzado")

@commands('trivial_stop')
def trivial_start(bot, trigger):
    global running_game
    if running_game == True:
        running_game = False
        global t
        t.cancel()

@commands('pista')
def pista(bot, trigger):
    bot.say(answerd.show_more_letters())

@commands('puntuacion')
def trivial_score(bot, trigger):
    bot.say(str(score))

@rule(".*")
@check_running_game
def test(bot, trigger):
    lock.acquire()
    if trigger.bytes.lower() == answerd.answerd.lower():
        # global t
        t.cancel()
        bot.say("minipunto para " + trigger.nick)
        score[trigger.nick]= score.get(trigger.nick,0)+1
        send_question(bot)
    lock.release()

def send_question(bot):
    question = random.choice(list_questions)
    global answerd
    answerd = Answerd(question.answerd)
    bot.say(question.question)
    # print question.answerd
    global t
    t = threading.Timer(INTERVAL, send_pista,(bot,))
    t.start()

def send_pista(bot):
    lock.acquire()
    if answerd.stop():
        bot.say("Respuesta no acertada. La respuesta era: " + answerd.answerd)
        send_question(bot)
    else:
        bot.say(answerd.show_more_letters())
        global t
        t = threading.Timer(INTERVAL, send_pista,(bot,))
        t.start()
    lock.release()