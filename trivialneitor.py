from willie.module import commands, rule
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

def check_running_game(f):  # pragma: no cover
    """Checks if the game is running or not"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if args[0].bot.memory['trivial_manager'].running_game:
            return f(*args, **kwargs)
        else:
            return None
    return decorated_function


def configure(config):
    """
    | [trivia_game] | example | purpose |
    | -------- | ------- | ------- |
    | path | ~/.willie/questions/ | Folder where are the files with the list_questions|
    | interval | 5 | time to display the next help |
    """
    if config.option('Configure trivia game module', False):
        config.add_section('trivia_game')
        config.interactive_add('trivia_game', 'path', 'folder path', '~/.willie/questions/')
        config.interactive_add('trivia_game', 'interval', 'time to display the next help', '5')

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
    list_questions = []
    for dirname, dirnames, filenames in os.walk(os.path.expanduser(bot.config.trivia_game.path)):
        for filename in filenames:
            with open (os.path.join(dirname, filename),'r') as f:
                for line in f:
                    l = line.split('*')
                    if len(l)==3:
                        list_questions.append(Question(l))
    if len(list_questions)==0:
        bot.say("No se ha cargado ninguna pregunta")

    bot.memory['trivial_manager'] = TrivialManager(bot,list_questions)
    global INTERVAL
    INTERVAL = int (bot.config.trivia_game.interval)


@commands('trivial')
def manage_trivia(bot, trigger):
    """Manage trivial game. For a list of commands, type: .trivial help"""
    bot.memory['trivial_manager'].manage_trivial(bot, trigger)

class TrivialManager:
    def __init__(self, bot, questions):
        # get a list of all methods in this class that start with _trivia_
        self.actions = sorted(method[9:] for method in dir(self) if method[:9] == '_trivial_')
        self.running_game = False
        self.lock = threading.Lock()
        # game's score
        self.score ={}
        # list with questions
        self.questions= questions
        # answerd of the current question
        self.answerd = None

    def send_question(self,bot):
        question = random.choice(self.questions)
        self.answerd = Answerd(question.answerd)
        bot.say(question.question)
        # print question.answerd
        self.t = threading.Timer(int (bot.config.trivia_game.interval), self.send_pista,(bot,))
        self.t.start()

    def send_pista(self,bot):
        self.lock.acquire()
        if self.answerd.stop():
            bot.say("Respuesta no acertada. La respuesta era: " + self.answerd.answerd)
            self.send_question(bot)
        else:
            bot.say(self.answerd.show_more_letters())
            self.t = threading.Timer(int (bot.config.trivia_game.interval), self.send_pista,(bot,))
            self.t.start()
        self.lock.release()

    def check_answerd(self,bot,trigger):

        self.lock.acquire()
        if trigger.bytes.lower() == self.answerd.answerd.lower():
            # global t
            self.t.cancel()
            bot.say("minipunto para " + trigger.nick)
            self.score[trigger.nick]= self.score.get(trigger.nick,0)+1
            self.send_question(bot)
        self.lock.release()


    def _show_doc(self, bot, command):
        """Given an trivial command, say the docstring for the corresponding method."""
        for line in getattr(self, '_trivial_' + command).__doc__.split('\n'):
            line = line.strip()
            if line:
                bot.reply(line)

    def manage_trivial(self, bot, trigger):
        """Manage trivial feeds. Usage: .trivial <command>"""
        text = trigger.group().split()
        if (len(text) < 2 or text[1] not in self.actions):
            bot.reply("Usage: .trivial <command>")
            bot.reply("Available trivial commands: " + ', '.join(self.actions))
            return
        getattr(self, '_trivial_' + text[1])(bot, trigger)

    def _trivial_start(self,bot,trigger):
        """Start trivia game. Usage: .trivial start
        In a near Future with option to select topic"""
        if self.running_game == False:
            self.running_game = True
            self.send_question(bot)
        else :
            bot.say("juego ya ha comenzado")
    
    def _trivial_stop(self,bot,trigger):
        """Stop trivia game. Usage: .trivial stop"""
        if self.running_game == True:
            self.running_game == False
            self.t.cancel()

    def _trivial_pista(self,bot, trigger):
        """Show a help more. Usage: .trivial pista"""
        if self.running_game:
            bot.say(self.answerd.show_more_letters())

    def _trivial_score(self,bot, trigger):
        """Show a score. Usage: .trivial score"""
        bot.say(str(self.score))

    def _trivial_help(self, bot, trigger):
        """Get help on any of the trivia game commands. Usage: .trivial help <command>"""
        command = trigger.group(4)
        if command in self.actions:
            self._show_doc(bot, command)
        else:
            bot.reply("For help on a command, type: .trivial help <command>")
            bot.reply("Available trivial commands: " + ', '.join(self.actions))

@rule(".*")
@check_running_game
def test(bot, trigger):
    bot.memory['trivial_manager'].check_answerd(bot,trigger)