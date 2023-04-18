import os, re, sys, json, signal, requests, telebot, openai, pandas as pd, numpy as np
from telebot import types
import tiktoken; enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
import pydub
import microsoft_azure as ms_azure

#--------------------------------------------------------------------------------------------------------------
# variables globales

DIR_FILE_PATH = '/'.join(sys.argv[0].replace('\\','/').split('/')[:-1])
DIR_FILE_PATH = DIR_FILE_PATH if DIR_FILE_PATH else "."

PATH_KEYS = '/'.join([DIR_FILE_PATH, 'keys.json'])
PATH_HISTORY = '/'.join([DIR_FILE_PATH,'chats-history'])

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

KEYS = json.load(open(PATH_KEYS))

chats = {}


#--------------------------------------------------------------------------------------------------------------
# configuración de la API de OpenAI y del bot de Telegram

SPEECH_KEY = os.getenv('SPEECH_KEY') if os.getenv('SPEECH_KEY') else KEYS['SPEECH_KEY']
SPEECH_REGION = os.getenv('SPEECH_REGION') if os.getenv('SPEECH_REGION') else KEYS['SPEECH_REGION']
ms_azure.set_speech_config(subscription=SPEECH_KEY, region=SPEECH_REGION)


OPENAI_KEY = os.getenv("OPENAI_KEY") if os.getenv("OPENAI_KEY") else KEYS['OPENAI_KEY']
openai.api_key = OPENAI_KEY


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") if os.getenv("TELEGRAM_TOKEN") else KEYS['TELEGRAM_TOKEN']
bot = telebot.TeleBot(TELEGRAM_TOKEN)


print('bot listo!',end='\n\n\n')

#--------------------------------------------------------------------------------------------------------------
# funciones

def error(msg=''):
    print(msg, end='\n\n')

def exist(username):
    return True if username in chats.keys() else False

def create_chat(msg):
    username = msg.from_user.username
    if not exist(username):
        chats[username] = Chat( msg=msg, history=ROLES[DEFAULT_ROLE] )
        return True
    return False

def get_user_by_chat_id(chat_id):
    for user, chat in chats.items():
        if chat.chat_id == chat_id:
            return user
    return None

def predict(chat):
    if chat.tokens > 4000:
        prompt = chat.get_bound( bound=4000 )
    else:
        prompt = chat.history

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=prompt
    )
    return response['choices'][0]['message']['content'].strip(' \n')


#--------------------------------------------------------------------------------------------------------------
# clases útiles

class Chat:
    def __init__(self, msg: types.Message, history: list=[]):
        self.user = msg.from_user.username
        self.chat_id = msg.chat.id
        self.first_name = msg.from_user.first_name

        self.history = history
        self.tokens = self.get_tokens_from_chat(history)
        self.length = len(history)

        self.file_in_use = ''
        self.role = self.get_role()

    def add(self, role, content):
        self.history.append({"role": role, "content": content})
        self.tokens += self.get_tokens(content)
        self.length += 1
        return self

    def __str__(self):
        return '\n'.join([f"{m['role']}: {m['content']}" for m in self.history])

    def get_bound(self, bound=4000):
        tokens=[]
        for message in self.history:
            tokens.append(self.get_tokens(message["content"]))
        
        temp = np.array(tokens)[::-1].cumsum()
        return self.history[-np.where(temp<bound)[0].max():]

    def get_tokens(self, text):
        return len(enc.encode(text))
    
    def get_tokens_from_chat(self, chat):
        tokens = 0
        for message in chat:
            tokens += self.get_tokens(message["content"])
        return tokens
    
    def get_role(self):
        if not self.history[0]['content']:
            print('1- Se obtuvo el rol: General assistant 🤖!',end='\n\n')
            return 'General assistant 🤖'

        for key, value in zip(ROLES.keys(), ROLES.values()):
            if key == 'General assistant 🤖':
                continue
            if value[0]['content'] == self.history[0]['content']:
                print(f'1- Se obtuvo el rol: {key}!',end='\n\n')
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
                chat = Chat(user=self.user, chat_id=self.chat_id, history=self.history[2:] + [{"role": "user", "content": prompt}])
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
        except:
            error('Error, no se pudo guardar el contexto actual.')
        
    def get_contents_files(self, extension='.json'):
        print('Se entró en la función get_contents_files():')
        try:
            path = '/'.join([PATH_HISTORY, self.user])
            files_name = [file for file in os.listdir(path) if file.endswith(extension)]
            contents = [file.capitalize().replace(extension,'') for file in files_name]

            print(f'1- Se obtuvieron los nombres de los archivos {extension}!',end='\n\n')
            return files_name, contents
        except:
            error('Error, no se pudo obtener los nombres de los archivos.')
            return [], []
        
    def get_content_from_file(self, file_name: str) -> list:
        print('Se entró en la función get_content_from_file():')
        try:
            path = '/'.join([PATH_HISTORY, self.user, file_name])
            content = pd.read_json(path).to_dict()

            print(f'1- Se obtuvo el registro a partir del archivo "{file_name}"!',end='\n\n')
            return [v for v in content.values()]
        except:
            error('Error, no se pudo cargar el contenido del archivo especificado.')
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
        print('Se entró en la función send_hello():')
        msg = bot.send_message(chat_id=self.chat_id, text=f'Hola {self.first_name} 👋. Mi rol actual es: {self.role} !')
        print('1- Se envió el mensaje de saludo al chat!')
        bot.pin_chat_message(chat_id=self.chat_id, message_id=msg.message_id)
        print('2- Se fijó el mensaje!',end='\n\n')

    def response_to(self, msg: types.Message):
        self.add("user", msg.text)
        temp = bot.reply_to(msg, '`Generando...`')

        response = predict(self)

        bot.send_message(chat_id=msg.chat.id, text=response)
        bot.delete_message(chat_id=temp.chat.id, message_id=temp.message_id)

        self.add("assistant", response)

    def new_chat(self):
        self.save_content()
        self.delete_content()
        self.file_in_use = ''
        self.send_hello()


#--------------------------------------------------------------------------------------------------------------
# funciones de manejo de señales

def handler_interrupt(signum, frame):
    for chat in chats.values():
        chat.save_content()
    raise KeyboardInterrupt
 
signal.signal(signal.SIGINT, handler_interrupt)


#--------------------------------------------------------------------------------------------------------------
# Bot Handlers


# comandos del bot:
# /newchat -> inicia nueva conversación
# /log -> muestra el contexto actual
# /load -> carga un contexto previamente guardado
# /rol -> cambia rol de chatgpt
# /read -> lee un mensaje de texto si se hace referencia al mensaje


@bot.message_handler(commands=['start'])
def start(msg):
    user = msg.from_user.username
    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.")
    chats[user].send_hello()
    print()


@bot.message_handler(commands=['read'])
def read_message(msg):
    user = msg.from_user.username
    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.")
    
    text = msg.reply_to_message.text
    
    ms_azure.text_to_speech(text, filename='temp.wav')
    bot.send_audio(chat_id=msg.chat.id, audio=open('temp.wav','rb'))
    os.remove('temp.wav')


# maneja el comando \newchat
@bot.message_handler(commands=['newchat'])
def newchat(msg):
    user = msg.from_user.username
    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.")
        chats[user].send_hello()
    else:
        chats[user].new_chat()
    print()


# maneja el comando \load
@bot.message_handler(commands=['load'])
def load_file_content(msg):
    user = msg.from_user.username

    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.") 
    
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

    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.")
    
    actual_content = '\n' + '\n'.join(['* ' + item['content'] for item in chats[user].history[2:] if item['role']=='user'])
    bot.send_message(chat_id=msg.chat.id, text=f'El contexto actual es: {actual_content}')


# maneja el comando \rol
@bot.message_handler(commands=['rol'])
def change_rol(msg):
    user = msg.from_user.username

    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.")
    
    rol_menu = [[types.InlineKeyboardButton(text = item, callback_data=item.lower())] for item in ROLES.keys()]
    keyboard = types.InlineKeyboardMarkup(rol_menu)
    bot.send_message(chat_id=msg.chat.id, text='Elije un rol para ChatGPT:', reply_markup=keyboard)


# maneja las entradas de texto al chat del bot
@bot.message_handler(content_types=['text'])
def reply_msg_handler(msg):    
    user = msg.from_user.username

    if create_chat(msg): 
        print(f"El ususario {user} inició una nueva conversación.")

    if msg.text in ['q', 'quit', 'Q', 'Quit', 'exit', 'Exit']:
        print('Deteniendo el bot...\n\n')
        bot.stop_bot()
        chats[user].save_content()
    else:
        chats[user].response_to(msg)


# maneja las descargas de archivos de audio y voz 
@bot.message_handler(content_types=['voice', 'audio'])
def handle_download_audio(message):
    user = message.from_user.username

    if create_chat(message): 
        print(f"El ususario {user} inició una nueva conversación.")
    
    if message.content_type == 'voice':
        file_info = bot.get_file(message.voice.file_id)
    elif message.content_type == 'audio':
        file_info = bot.get_file(message.audio.file_id)

    msg = bot.send_message(chat_id=message.chat.id, text='`Descargando audio...`')
    
    download_url = f'https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}'

    response = requests.get(download_url).content
    with open('output.ogg', 'wb') as f:
        f.write(response)

    sound = pydub.AudioSegment.from_ogg("output.ogg")
    sound.export("output.wav", format='wav')
    os.remove('output.ogg')

    msg = bot.edit_message_text(text='`Convirtiendo audio...`', chat_id=msg.chat.id, message_id=msg.message_id)

    try:
        text = ms_azure.speech_to_text('output.wav')
    except:
        text = '`No se pudo reconocer el audio`'

    os.remove('output.wav')

    msg = bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=msg.message_id)
    chats[user].response_to(msg)




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

    print()


#--------------------------------------------------------------------------------------------------------------
# Activa el bot

bot.polling()
