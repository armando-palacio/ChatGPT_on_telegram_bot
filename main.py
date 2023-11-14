import os, re, sys, json, time, signal, requests, telebot, pandas as pd, numpy as np
from telebot import types
from openai import OpenAI
import tiktoken; enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
from pathlib import Path
import pydub, io
#--------------------------------------------------------------------------------------------------------------
# variables globales

DIR_FILE_PATH = Path(__file__).parent
PATH_KEYS = DIR_FILE_PATH / 'keys.json'
PATH_HISTORY = DIR_FILE_PATH / 'chats-history'

if not os.path.isdir(PATH_HISTORY):
    os.mkdir(PATH_HISTORY)

DEFAULT_ROLE = 'Python coding 🐍'

ROLES = {
    'General assistant 🤖': [{"role":"user","content":""},{"role":"assistant","content":""}],
    'Python coding 🐍':[{"role": "user", "content": "Como aspirante a programador en Python, me gustaría que me proporciones consejos y recursos para mejorar mis habilidades de programación en este lenguaje. Me gustaría conocer las mejores prácticas, técnicas de depuración, manejo de excepciones, gestión de datos, uso de bibliotecas y cualquier otra habilidad que me pueda ayudar a mejorar como programador en Python. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus consejos en la práctica. Si entendiste devolveme un ok."},
        {"role": "assistant", "content": f"ok"}],
    'Optical communication ing. 🛰':[{"role": "user", "content": "Como profesional en el campo de las comunicaciones ópticas satelitales, me gustaría que me proporciones una visión general de los principales desafíos y oportunidades en este campo. Me gustaría conocer las tecnologías más recientes, la normativa y las tendencias actuales en las comunicaciones ópticas satelitales. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus conocimientos en la práctica y desarrollar mi carrera en este campo. Si entendiste devolveme un ok."},
        {"role": "assistant", "content": f"ok"}],
}

try:
    KEYS = {'OPENAI_KEY': os.environ['OPENAI_API_KEY'], 'TELEGRAM_TOKEN': os.environ['TELEGRAM_TOKEN']}
except:
    KEYS = json.load(open(PATH_KEYS))

chats = {}

#--------------------------------------------------------------------------------------------------------------
# configuración de la API de OpenAI y del bot de Telegram

client = OpenAI(api_key=KEYS['OPENAI_KEY'])

TELEGRAM_TOKEN = KEYS['TELEGRAM_TOKEN']

#--------------------------------------------------------------------------------------------------------------
# funciones
def voice2text(filename):
    file = open(filename, "rb")
    response = client.audio.transcriptions.create(
        model="whisper-1", 
        file= file
    )
    file.close()
    return response.text

def text2voice(text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="echo",
        input=text
    )
    response.stream_to_file(DIR_FILE_PATH / "temp.mp3")
    return open('temp.mp3','rb')

def _print_(*msg):
    print(*msg, end='\n\n')

def exist(username):
    return True if username in chats.keys() else False

def create_temp_file(user):
    endpoint = {}
    endpoint['chat'] = chats[user].__dict__

    if not os.path.isdir(f'{PATH_HISTORY}/{user}'):
        os.mkdir(f'{PATH_HISTORY}/{user}')

    with open(f'{PATH_HISTORY}/{user}/~temp.json', 'w') as f:
        json.dump(endpoint, f)

def get_temp_file(user):
    if not os.path.isdir(f'{PATH_HISTORY}/{user}'):
        return

    with open(f'{PATH_HISTORY}/{user}/~temp.json', 'r') as f:
        endpoint = json.load(f)
    return endpoint

def delete_temp_file(user):
    if not os.path.isdir(f'{PATH_HISTORY}/{user}'):
        return
    os.remove(f'{PATH_HISTORY}/{user}/~temp.json')

def create_chat(msg):
    username = msg.from_user.username
    if not exist(username):
        chats[username] = Chat( msg=msg, history=ROLES[DEFAULT_ROLE] )
        create_temp_file(username)
        return True
    return False

def get_user_by_chat_id(chat_id):
    for user, chat in chats.items():
        if chat.chat_id == chat_id:
            return user
    return None

def predict(chat):
    prompt = chat.get_bound( bound=4000 )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=prompt
    )
    return response.choices[0].message.content


#--------------------------------------------------------------------------------------------------------------
# clases útiles

class Chat:
    def __init__(self, msg: types.Message=None, chat=None, from_dict :dict=None, history: list=[]):
        if msg:	
            self.user = msg.from_user.username
            self.chat_id = msg.chat.id
            self.first_name = msg.from_user.first_name
            
            self.history = history
            self.tokens = self.get_tokens_from_chat(history)
            self.length = len(history)
            
            self.file_in_use = ''
            self.role = self.get_role()
            self.pinned_msg_id = None
            print(f'Se creó un nuevo chat para el usuario `{msg.from_user.username}`')
            _print_(f'role: `{self.role}`')
        elif chat:
            self.user = chat.user
            self.chat_id = chat.chat_id
            self.first_name = chat.first_name
			
            self.history = chat.history
            self.tokens = chat.tokens
            self.length = chat.length
			
            self.file_in_use = chat.file_in_use
            self.role = chat.role
            self.pinned_msg_id = chat.pinned_msg_id
        elif from_dict:
            self.user = from_dict['user']
            self.chat_id = from_dict['chat_id']
            self.first_name = from_dict['first_name']
            
            self.history = from_dict['history']
            self.tokens = from_dict['tokens']
            self.length = from_dict['length']
            
            self.file_in_use = from_dict['file_in_use']
            self.role = from_dict['role']
            self.pinned_msg_id = from_dict['pinned_msg_id']

    def add(self, role, content):
        self.history.append({"role": role, "content": content})
        self.tokens += self.get_tokens(content)
        self.length += 1
        return self

    def copy(self):
        return Chat(chat=self)

    def __str__(self):
        return '\n'.join([f"{m['role']}: {m['content']}" for m in self.history])

    def get_bound(self, bound=4000):
        tokens=[]
        for message in self.history:
            tokens.append(self.get_tokens(message["content"]))
        
        temp = np.array(tokens)[::-1].cumsum()
        return np.array(self.history, dtype=object)[temp[::-1]<bound].tolist()

    def get_tokens(self, text):
        return len(enc.encode(text))
    
    def get_tokens_from_chat(self, chat):
        tokens = 0
        for message in chat:
            tokens += self.get_tokens(message["content"])
        return tokens
    
    def get_role(self):
        if not self.history[0]['content']:
            return 'General assistant 🤖'

        for key, value in zip(ROLES.keys(), ROLES.values()):
            if key == 'General assistant 🤖':
                continue
            if value[0]['content'] == self.history[0]['content']:
                return key
    
    def set_role(self, role):
        if role == self.role:
            return
        self.save_content()
        self.history = ROLES[role]
        self.tokens = self.get_tokens_from_chat(self.history)
        self.length = len(self.history)
        self.role = role
        self.file_in_use = ''
        print(f'Se fijó el rol {self.role} en el chat del usuario {self.user}!')
        self.send_hello()

    def delete_content(self):
        self.history = self.history[:2]
        self.tokens = self.get_tokens_from_chat(self.history)
        self.length = len(self.history)
        print(f'Se eliminó el historial del chat del usuario {self.user}!')

    def save_content(self):
        try:
            if self.length > 2:
                print(f'Guardando el chat del usuario {self.user}!')
                if self.file_in_use: # verificamos si se está usando un archivo
                    path = '/'.join([PATH_HISTORY, self.user])
                    if not os.path.exists(path): # verificamos si existe una carpeta para el usuario
                        os.mkdir(path)
                    path = '/'.join([path, self.file_in_use])
                    if os.path.exists(path): # verificamos si existe el archivo
                        pd.DataFrame(self.history).T.to_json(path)
                        print('Se guardó el archivo',end='\n\n')
                        return
                    self.file_in_use = '' # si el archivo no existe, se limpia la variable file_in_use

                # si no se está usando un archivo o el archivo en uso ya no existe, se guarda en un nuevo archivo
                prompt = "Elije un título para la conversación basado en el contexto actual, que NO exceda las 5 palabras."
                chat = self.copy()
                chat.history = chat.history[2:] + [{"role": "user", "content": prompt}]
                response = predict(chat).strip('.')

                regex = re.compile('[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_\-.\s]+')
                response = regex.sub('', response)
                
                path = '/'.join([PATH_HISTORY, self.user])
                if not os.path.exists(path): # verificamos si existe una carpeta para el usuario
                    os.mkdir(path)

                path = '/'.join([path, f'{response.lower()}.json'])
                pd.DataFrame(self.history).T.to_json(path)
                self.file_in_use = f'{response.lower()}.json'
                print('Se guardó el archivo',end='\n\n')
        except Exception as e:
            _print_('Error in `save_content()`:', e)
        
    def get_contents_files(self, extension='.json'):
        print('Se entró en la función get_contents_files():')
        try:
            path = '/'.join([PATH_HISTORY, self.user])
            files_name = [file for file in os.listdir(path) if file.endswith(extension)]
            contents = [file.capitalize().replace(extension,'') for file in files_name]

            print(f'1- Se obtuvieron los nombres de los archivos {extension}!',end='\n\n')
            return files_name, contents
        except Exception as e:
            _print_('Error in `get_contents_files()`:', e)
            return [], []
        
    def get_content_from_file(self, file_name: str) -> list:
        print('Se entró en la función get_content_from_file():')
        try:
            path = '/'.join([PATH_HISTORY, self.user, file_name])
            content = pd.read_json(path).to_dict()

            print(f'1- Se obtuvo el registro a partir del archivo "{file_name}"!',end='\n\n')
            return [v for v in content.values()]
        except Exception as e:
            _print_('Error in `get_content_from_file()`:', e)
            return []
        
    def set_content_from_file(self, file_name: str):
        content = self.get_content_from_file(file_name)

        if not content:
            bot.send_message(chat_id=self.chat_id, text='No se pudo cargar el historial de este chat 🤷‍♂️')
            return

        self.save_content()
        self.history = content
        self.tokens = self.get_tokens_from_chat(self.history)
        self.length = len(self.history)
        self.role = self.get_role()
        self.file_in_use = file_name
        self.send_hello()

    def send_hello(self):
        print(f'Enviando saludo al usuario `{self.user}`')
        msg = bot.send_message(chat_id=self.chat_id, text=f'Hola {self.first_name} 👋. Mi rol actual es: {self.role} !')
        
        if self.pinned_msg_id is not None:
            bot.unpin_chat_message(chat_id=self.chat_id, message_id=self.pinned_msg_id)
        self.pinned_msg_id = msg.message_id
        
        bot.pin_chat_message(chat_id=self.chat_id, message_id=self.pinned_msg_id)
        _print_('Se fijó el mensaje de saludo')

    def response_to_text(self, msg: types.Message):
        bot.send_chat_action(msg.chat.id, 'typing')
        self.add("user", msg.text)
        response = predict(self)
        bot.send_message(chat_id=msg.chat.id, text=response)
        self.add("assistant", response)

    def response_to_voice(self, msg: types.Voice):
        bot.send_chat_action(msg.chat.id, 'record_audio')

        voice_bytes = bot.download_file( bot.get_file(msg.voice.file_id).file_path )
        bot.send_chat_action(msg.chat.id, 'record_audio')

        with open('output.ogg', 'wb') as f:
            f.write(voice_bytes)

        input_text = voice2text('output.ogg'); os.remove('output.ogg')
        bot.send_chat_action(msg.chat.id, 'record_audio')

        self.add("user", input_text)

        output_text = predict(self)

        self.add("assistant", output_text)
        bot.send_chat_action(msg.chat.id, 'record_audio')

        output_voice = text2voice(output_text)
        bot.send_voice(chat_id=msg.chat.id, voice=output_voice); output_voice.close(); os.remove('temp.mp3')

    def new_chat(self):
        self.save_content()
        self.delete_content()
        self.file_in_use = ''
        self.send_hello()


#--------------------------------------------------------------------------------------------------------------
# funciones de manejo de señales

def handler_interrupt(signum, frame):
    for chat in chats.values():
        create_temp_file(chat.user)
    raise SystemExit('Deteniendo el bot...')
 
signal.signal(signal.SIGINT, handler_interrupt)


#--------------------------------------------------------------------------------------------------------------
# Bot Handlers


# comandos del bot:
# newchat - inicia nueva conversación
# log - muestra el contexto actual
# load - carga un contexto previamente guardado
# setrol - cambia rol de chatgpt
# read - lee un mensaje de texto si se hace referencia al mensaje

# comandos de testeo:
# user - muestra el usuario actual
# rol - muestra el rol actual


for user in os.listdir(PATH_HISTORY):
    path = f'{PATH_HISTORY}/{user}/~temp.json'
    if os.path.exists(path):
        _dict_ = json.load(open(path))
        chats[user] = Chat( from_dict=_dict_['chat'] )
        print('Se recuperó el chat de:', user)


print('The bot is ready!!',end='\n\n\n')

while True:
    try:
        bot = telebot.TeleBot(TELEGRAM_TOKEN)


        @bot.message_handler(commands=['start'])
        def start(msg):
            user = msg.from_user.username
            create_chat(msg) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario

            chats[user].send_hello()
            create_temp_file(user)
            print()


        @bot.message_handler(commands=['user'])
        def start(msg):
            user = msg.from_user.username
            create_chat(msg) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario
            bot.send_message(chat_id=msg.chat.id, text=f'El usuario actual es: @{user}')
            print()


        @bot.message_handler(commands=['rol'])
        def start(msg):
            user = msg.from_user.username
            create_chat(msg) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario
            bot.send_message(chat_id=msg.chat.id, text=f'El rol actual es: {chats[user].role}')
            print()


        @bot.message_handler(commands=['read'])
        def read_message(msg):
            create_chat(msg) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario
            
            text = msg.reply_to_message.text
            
            response = client.audio.speech.create(
              model="tts-1",
              voice="echo",
              input=text
            )
            response.stream_to_file(DIR_FILE_PATH / "temp.mp3")
            bot.send_voice(chat_id=msg.chat.id, voice=open('temp.mp3','rb'))
            os.remove('temp.mp3')


        # maneja el comando \newchat
        @bot.message_handler(commands=['newchat'])
        def newchat(msg):
            user = msg.from_user.username
            if create_chat(msg):
                chats[user].send_hello()
            else:
                chats[user].new_chat()
            create_temp_file(user)
            print()


        # maneja el comando \load
        @bot.message_handler(commands=['load'])
        def load_file_content(msg):
            user = msg.from_user.username
            create_chat(msg) # crea un nuevo chat SI no existe el usuario
            
            _, contents = chats[user].get_contents_files(extension='.json')

            if not contents:
                bot.send_message(chat_id=msg.chat.id, text='No se encontraron conversaciones previas 🤷‍♂️')
            else:
                menu = [[types.InlineKeyboardButton(text = content, callback_data=content.lower())] for content in contents]
                keyboard = types.InlineKeyboardMarkup(menu)
                bot.send_message(chat_id=msg.chat.id, text='Elije un contexto para cargar:', reply_markup=keyboard)


        # maneja el comando \log
        @bot.message_handler(commands=['log'])
        def show_log(msg):
            user = msg.from_user.username
            create_chat(msg) # crea un nuevo chat SI no existe el usuario
            
            actual_content = '\n' + '\n'.join(['* ' + item['content'] for item in chats[user].history[2:] if item['role']=='user'])
            bot.send_message(chat_id=msg.chat.id, text=f'El contexto actual es: {actual_content}')


        # maneja el comando \setrol
        @bot.message_handler(commands=['setrol'])
        def change_rol(msg):
            create_chat(msg) # crea un nuevo chat SI no existe el usuario
            
            rol_menu = [[types.InlineKeyboardButton(text = item, callback_data=item.lower())] for item in ROLES.keys()]
            keyboard = types.InlineKeyboardMarkup(rol_menu)
            bot.send_message(chat_id=msg.chat.id, text='Elije un rol para ChatGPT:', reply_markup=keyboard)


        # maneja las entradas de texto al chat del bot
        @bot.message_handler(content_types=['text'])
        def reply_msg_handler(msg):    
            user = msg.from_user.username
            create_chat(msg)

            if msg.text.startswith('/'):
                bot.send_message(chat_id=msg.chat.id, text='No puedo reconocer este comando 😕')
                return
            chats[user].response_to_text(msg)
            create_temp_file(user)


        # maneja las descargas de archivos de audio y voz 
        @bot.message_handler(content_types=['voice'])
        def handle_download_audio(message):
            user = message.from_user.username
            create_chat(message)
            chats[user].response_to_voice(message)
            create_temp_file(user)


        # maneja las pulsaciones de botones de los menús
        @bot.callback_query_handler(func=lambda call: True)
        def callback_query(call):
            chat_id = call.message.chat.id
            user = get_user_by_chat_id(chat_id)

            if not exist(user):
                bot.send_message(chat_id=call.message.chat.id, text='No hay registro de este usuario. Presiona /newchat para iniciar una nueva conversación.')
                return
            
            files_name, contents = chats[user].get_contents_files('.json')
            call_data = call.data.capitalize()
            z = dict(zip(contents, files_name))

            if call_data in z.keys(): # carga un contexto previamente guardado
                chats[user].set_content_from_file(z[call_data])

            elif call_data in ROLES.keys(): # cambia el rol de chatgpt
                chats[user].set_role(call_data)

            create_temp_file(user)
            print()

        #--------------------------------------------------------------------------------------------------------------
        # Activa el bot

        bot.polling()

    except requests.exceptions.ReadTimeout:
        print('timeout!')
    except requests.exceptions.ConnectionError:
        print('error de conexión!')
        time.sleep(5)
