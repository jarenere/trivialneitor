# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from willie.module import commands, rule
import willie.bot
import random
from functools import wraps
import threading
import os.path
import sys  
import argparse
from unidecode import unidecode

reload(sys)  
sys.setdefaultencoding('utf-8')


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

class Team:
    count = 1
    def __init__(self, players):
        self.players=players
        self.score=0
        self.number_team = self.__class__.count
        self.__class__.count += 1
    def __str__(self):    
        return "Team{0}: players: {1}. Score: {2}".format(str(self.number_team),', '.join(self.players),self.score)
    def __repr__(self):
        return "Team{0}: players: {1}. Score: {2}".format(str(self.number_team),', '.join(self.players),self.score)
    def search_score(self,player):
        #search user and increment in 1 if user exist and return True else False
        if player in self.players:
            self.score = self.score + 1
            return True
        else:
            return False
    def team(self):
        return  "Team{0}".format(self.number_team)

class Question:
    def __init__(self, str):
        l = str.split('©')
        if len (l) != 2: raise Exception('Wrong question format, two or more ©') 
        self.theme = l[0].lower()
        l = l[1].split('«')
        if len (l) != 2: raise Exception('Wrong question format, two or more «')
        self.autor= l[0]
        l = l[1].split('*')
        if len (l) != 2: raise Exception('Wrong question format, two or more *')
        self.question = l[0]
        self.answerd = l[1].replace('\n','').replace('\r','')

def setup(bot):
    list_questions = []
    for dirname, dirnames, filenames in os.walk(os.path.expanduser(bot.config.trivia_game.path)):
        for filename in filenames:
            with open (os.path.join(dirname, filename),'r') as f:
                for i,line in enumerate(f):
                    try:
                        list_questions.append(Question(line))
                    except Exception as e:
                        print "error, file {0}, line {1} ({2}): ".format(os.path.join(dirname, filename),i, e)
    if len(list_questions)==0:
        print("No se ha cargado ninguna pregunta")

    bot.memory['trivial_manager'] = TrivialManager(bot,list_questions)


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
        self.ddbb_questions= questions
        # self.questions = None
        # answerd of the current question
        self.answerd = None

    def send_question(self,bot):
        if self.i_question <= self.number_question:
            question = random.choice(self.questions)
            self.answerd = Answerd(question.answerd)
            bot.say("{0}/{1}|{2}".format(self.i_question,self.number_question,question.question))
            self.i_question += 1
            self.t = threading.Timer(int (bot.config.trivia_game.interval), self.send_pista,(bot,))
            self.t.start()
        else:
            #finish game
            self.endgame(bot)

    def _score(self):
        """return a readable score"""
        text = ""
        for team in self.teams:
            text= text + str(team)+" || "
        for i, [name, score] in enumerate(self.score.iteritems()):
            if i == 0:
                text = text + "Players: "
            text = text + str(name) + ": " + str(score) + " || "
        return text

    def _score_eol(self):
        text = "Puntuación trivial:\n"
        for i, member in enumerate(self.teams):
            if i == 0:
                text = "Teams:\n"
            text = "[list]" + str(member) + "[/list]\n"
        for i, [name, score] in enumerate(self.score.iteritems()):
            if i == 0:
                text = text + "Players:\n"
            text = text +"[list]" + str(name) + ": " + str(score) +"[/list]\n"
        text = text + "[size=70]powered by nu_kru and Zokormazo[/size]"
        return text


    def endgame(self,bot):
        """stop game and reset score"""
        bot.say("Endgame, score:")
        bot.say(self._score())
        # check if exist eol_manager
        if bot.memory.has_key('eol_manager'):
            # check if method exist
            if "post" in dir(bot.memory['eol_manager']):
                bot.memory['eol_manager'].post(self._score_eol)
        self.score={}
        self.teams=[]
        self.running_game=False

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
        if unidecode(trigger.bytes.lower()) == unidecode(self.answerd.answerd.lower()):
            self.t.cancel()
            check=False
            for team in self.teams:
                if team.search_score(trigger.nick):
                    bot.say("minipunto para el equipo" + team.team())
                    check=True
            if not check:
                # user does not belong to any team
                bot.say("minipunto para " + trigger.nick)
                self.score[str(trigger.nick)]= self.score.get(str(trigger.nick),0)+1
            for name, score in self.score.iteritems():
                if score >= self.points_to_win and self.points_to_win!=0:
                    self.endgame(bot)
            for team in self.teams:
                if team.score>=self.points_to_win and self.points_to_win!=0:
                    self.endgame(bot)
            if self.running_game:
                # game not finished
                self.send_question(bot)
        self.lock.release()


    def _show_doc(self, bot, command):
        """Given an trivial command, say the docstring for the corresponding method."""
        for line in getattr(self, '_trivial_' + command).__doc__.split('\n'):
            line = line.strip()
            if line:
                bot.reply(line)

    def argumentParser(self,bot,trigger):
        """split argument parser and show info/error"""
        parser = argparse.ArgumentParser(".trivial start",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-t','--theme',nargs='*',help='execute trivial only with theme selected',default=[])
        parser.add_argument('-n','--number-question',nargs='?',type=int,const='15', default='15',help='number question of game.',choices=xrange(1, 1000),metavar='choose from 1..1000')
        parser.add_argument('-p','--points-to-win',nargs='?',type=int,const='0', default='0',help='number points to win, if you reach this punctuation before finishing the game, this ends immediately. 0 to no reach this punctuation',choices=xrange(0, 1000),metavar='choose from 0...1000')
        parser.add_argument("-team",nargs ='*',action='append', default=[], help='trivial with teams, example -team user1 user2 -team user3')
        
        #disable stdout
        f = open(os.devnull, 'w')
        stderr_aux = sys.stderr
        stdout_aux = sys.stdout
        sys.stdout = f
        sys.stderr = f
        try:
            args = parser.parse_args(trigger.bytes.lower().split()[2:])   
        except:
            if trigger.bytes.lower().split()[2:] ==['-h']:
                for line in parser.format_help().split('\n'):
                    bot.notice(line,recipient=trigger.nick)
            else:
                for line in parser.format_usage().split('\n'):
                     bot.say(line)
            #enable stderr
            sys.stderr = stderr_aux
            raise
        #enable stderr
        sys.stderr = stderr_aux
        sys.stdout = stdout_aux
        return args

    def select_questions(self,bot,themes):
        """Select questions by theme"""
        myset = set(themes)
        if len(myset) !=0:
            themes = self._themes()
            for i in myset:
                if i not in themes:
                    bot.say("Theme {0} not found".format(i))
                    raise Exception 
            l =  [i for i in self.ddbb_questions if i.theme in myset]
            self.questions = l
        else:
            self.questions=self.ddbb_questions

    def select_teams(self,bot,teams):
        self.teams = []
        list_users = []
        for channel in bot.channels:
            for i in bot.privileges[channel]:
                list_users.append(i)
        for team in teams:
            for user in team:
                if  user not in list_users:
                    bot.say("User {0} not found".format(user))
                    raise Exception ("error in team")
        for team in teams:
            # create list of teams
            if len(team)>0:
                self.teams.append(Team(team))


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
        to see more options .trivial start -h"""
        if self.running_game == False:
            if len(self.ddbb_questions)==0:
                bot.say("no hay ninguna pregunta cargada")
            else:
                try:
                    args = self.argumentParser(bot,trigger)
                    self.select_questions(bot,args.theme)
                    self.select_teams(bot,args.team)
                except Exception as e:
                    return
                self.number_question = args.number_question # gnumber of questions in the game
                self.points_to_win = args.points_to_win
                self.i_question = 1 # number ot question
                self.send_question(bot)
                self.running_game = True
        else :
            bot.say("juego ya ha comenzado")
    
    def _trivial_stop(self,bot,trigger):
        """Stop trivia game. Usage: .trivial stop"""
        if self.running_game == True:
            self.running_game = False
            self.t.cancel()

    def _trivial_pista(self,bot, trigger):
        """Show a help more. Usage: .trivial pista"""
        if self.running_game:
            bot.say(self.answerd.show_more_letters())

    def _trivial_score(self,bot, trigger):
        """Show a score. Usage: .trivial score"""
        bot.say(self._score())

    def _themes(self):
        """Retur list of themes"""
        return set([i.theme for i in self.ddbb_questions])

    def _trivial_themes(self,bot, trigger):
        """Show topics available in the questions. Usage: .trivial themes"""
        # cache decorator or even easier, upload theme ready to start
        bot.say(str(self._themes()))

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