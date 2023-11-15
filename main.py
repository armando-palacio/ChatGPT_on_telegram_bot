import os, json, time, signal, requests, telebot

from utils import *

chats = {}

#--------------------------------------------------------------------------------------------------------------
# funciones de manejo de señales

def handler_interrupt(signum, frame):
    for chat in chats.values():
        chat.create_temp_file()
    raise SystemExit('Deteniendo el bot...')
 
signal.signal(signal.SIGINT, handler_interrupt)


#--------------------------------------------------------------------------------------------------------------
# Bot Handlers


# comandos del bot:
# newchat - inicia nuevo chat
# setrol - cambia de rol a ChatGPT
# read - crea un speech del mensaje de texto referenciado o del texto escrito luego del comando
# write - transcribe el audio referenciado a texto
# log - muestra todas las entradas del ususario
# load - carga un chat del historial de conversaciones
# user - muestra el usuario actual
# rol - muestra el rol actual de ChatGPT


for user in os.listdir(PATH_HISTORY):
    _dict_ = get_temp_file(user)
    if _dict_:
        chats[user] = Chat( from_dict=_dict_['chat'] )
        print('Se recuperó el chat de:', user)


print('The bot is ready!!',end='\n\n\n')

while True:
    try:
        bot = telebot.TeleBot( os.environ['TELEGRAM_TOKEN'] )


        @bot.message_handler(commands=['start'])
        def start(msg):
            user = msg.from_user.username
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario

            chats[user].send_hello(bot) # envía el mensaje de bienvenida al usuario
            chats[user].create_temp_file() # guarda el estado actual del chat en un archivo temporal ~temp.json


        @bot.message_handler(commands=['user'])
        def start(msg):
            user = msg.from_user.username
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario
            bot.send_message(chat_id=msg.chat.id, text=f'El usuario actual es: @{user}')


        @bot.message_handler(commands=['rol'])
        def start(msg):
            user = msg.from_user.username
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario
            bot.send_message(chat_id=msg.chat.id, text=f'El rol actual es: {chats[user].role}')


        @bot.message_handler(commands=['read'])
        def read_message(msg):
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario
            
            if msg.content_type != 'text':
                bot.send_message(chat_id=msg.chat.id, text='Haz referencia a algún mensaje de texto que quieras que lea o escribe el texto luego del comando `/read` (ej: /read Hello Arche!)')
                return
            if msg.reply_to_message:
                text = msg.reply_to_message.text
            else:
                text = msg.text.split('/read')[-1]

            try: 
                file = text2voice(text)
                bot.send_voice(chat_id=msg.chat.id, voice=file)
                file.close(); os.remove('temp.mp3')
            except Exception as e:
                print(e)
                bot.send_message(chat_id=msg.chat.id, text='Haz referencia a algún mensaje de texto que quieras que lea o escribe el texto luego del comando `/read` (ej: /read Hello Arche!)')


        @bot.message_handler(commands=['write'])
        def write_message(msg):
            user = msg.from_user.username
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario y un archivo temporal ~temp.json en la carpeta del historial del usuario

            if msg.reply_to_message:
                if msg.reply_to_message.content_type != 'voice':
                    bot.send_message(chat_id=msg.chat.id, text='Haz referencia a algún mensaje de voz que quieras que transcriba.')
                    return
                chats[user].transcript_to_text(msg.reply_to_message, bot)
            else:
                bot.send_message(chat_id=msg.chat.id, text='Haz referencia a algún mensaje de `voz` que quieras que transcriba.')
                return
        

        @bot.message_handler(commands=['newchat'])
        def newchat(msg):
            user = msg.from_user.username
            if create_chat(msg, chats):
                chats[user].send_hello(bot)
            else:
                chats[user].new_chat(bot)


        @bot.message_handler(commands=['load'])
        def load_file_content(msg):
            user = msg.from_user.username
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario
            
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
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario
            
            actual_content = '\n' + '\n'.join(['* ' + item['content'] for item in chats[user].history[2:] if item['role']=='user'])
            bot.send_message(chat_id=msg.chat.id, text=f'El contexto actual es: {actual_content}')


        # maneja el comando \setrol
        @bot.message_handler(commands=['setrol'])
        def change_rol(msg):
            create_chat(msg, chats) # crea un nuevo chat SI no existe el usuario
            
            rol_menu = [[types.InlineKeyboardButton(text = item, callback_data=item.lower())] for item in ROLES.keys()]
            keyboard = types.InlineKeyboardMarkup(rol_menu)
            bot.send_message(chat_id=msg.chat.id, text='Elije un rol para ChatGPT:', reply_markup=keyboard)


        # maneja las entradas de texto al chat del bot
        @bot.message_handler(content_types=['text'])
        def reply_msg_handler(msg):    
            user = msg.from_user.username
            create_chat(msg, chats)

            if msg.text.startswith('/'):
                bot.send_message(chat_id=msg.chat.id, text='No puedo reconocer este comando 😕')
                return
            chats[user].response_to_text(msg, bot)


        # maneja las descargas de archivos de audio y voz 
        @bot.message_handler(content_types=['voice'])
        def handle_download_audio(message):
            user = message.from_user.username
            create_chat(message, chats)
            chats[user].response_to_voice(message)


        # maneja las pulsaciones de botones de los menús
        @bot.callback_query_handler(func=lambda call: True)
        def callback_query(call):
            chat_id = call.message.chat.id
            user = get_user_by_chat_id(chat_id, chats)

            if not exist(user, chats):
                bot.send_message(chat_id=call.message.chat.id, text='No hay registro de este usuario. Presiona /newchat para iniciar una nueva conversación.')
                return
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            
            files_name, contents = chats[user].get_contents_files('.json')
            call_data = call.data.capitalize()
            z = dict(zip(contents, files_name))

            if call_data in z.keys(): # carga un contexto previamente guardado
                chats[user].set_content_from_file(z[call_data], bot)

            elif call_data in ROLES.keys(): # cambia el rol de chatgpt
                chats[user].set_role(call_data, bot)

            chats[user].create_temp_file()

        #--------------------------------------------------------------------------------------------------------------
        # Activa el bot

        bot.polling()

    except requests.exceptions.ReadTimeout:
        print('timeout!')
    except requests.exceptions.ConnectionError:
        print('error de conexión!')
        time.sleep(5)
