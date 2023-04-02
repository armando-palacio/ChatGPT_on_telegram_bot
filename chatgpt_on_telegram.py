import os, json, time, telebot, openai, pandas as pd
from telebot import types

keys = json.load(open('keys.txt'))

openai.api_key = keys["OPENAI_KEY"]

path_history = './ChatGPT-history/'

file_in_use = ''
actual_rol = 'Python coding 🐍'
chat_log =  [{"role": "user", "content": "Como aspirante a programador en Python, me gustaría que me proporciones consejos y recursos para mejorar mis habilidades de programación en este lenguaje. Me gustaría conocer las mejores prácticas, técnicas de depuración, manejo de excepciones, gestión de datos, uso de bibliotecas y cualquier otra habilidad que me pueda ayudar a mejorar como programador en Python. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus consejos en la práctica. Si entendiste devolveme un ok."},
            {"role": "assistant", "content": f"ok"}]

rols = {
    'General assistant 🤖': [{"role":"user","content":""},{"role":"assistant","content":""}],
    'Python coding 🐍':[{"role": "user", "content": "Como aspirante a programador en Python, me gustaría que me proporciones consejos y recursos para mejorar mis habilidades de programación en este lenguaje. Me gustaría conocer las mejores prácticas, técnicas de depuración, manejo de excepciones, gestión de datos, uso de bibliotecas y cualquier otra habilidad que me pueda ayudar a mejorar como programador en Python. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus consejos en la práctica. Si entendiste devolveme un ok."},
        {"role": "assistant", "content": f"ok"}],
    'Optical communication ing. 🛰':[{"role": "user", "content": "Como profesional en el campo de las comunicaciones ópticas satelitales, me gustaría que me proporciones una visión general de los principales desafíos y oportunidades en este campo. Me gustaría conocer las tecnologías más recientes, la normativa y las tendencias actuales en las comunicaciones ópticas satelitales. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus conocimientos en la práctica y desarrollar mi carrera en este campo. Si entendiste devolveme un ok."},
        {"role": "assistant", "content": f"ok"}],
}



TELEGRAM_TOKEN = keys["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)
print('bot listo!',end='\n\n\n')

# comandos:
# /newchat -> inicia nueva conversación
# /log -> muestra el contexto actual
# /load -> carga un contexto previamente guardado
# /rol -> cambia rol de chatgpt

def error(msg=''):
    print(msg, end='\n\n')
    bot.stop_bot()
    save_content()
    time.sleep(3)


def predict(chat_log):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chat_log
    )
    return response['choices'][0]['message']['content'].strip(' \n')


def delete_content():
    global chat_log
    print(f'Se entró en la función {delete_content.__name__}():')
    print('1- Se eliminó el contexto actual. Longitud del registro: 2',end='\n\n')
    chat_log =  chat_log[:2]


def save_content():
    global file_in_use

    if not os.path.isdir(path_history):
        os.mkdir(path_history)

    try:
        print(f'Se entró en la función {save_content.__name__}():')
        print('1- Longitud del registro:', len(chat_log))

        pasos = 2

        if len(chat_log)>2:
            if file_in_use: # si se está usando un archivo, se guarda en ese
                print(f'{pasos}- Se cargó el chat actual desde un archivo!'); pasos+=1

                if os.path.exists(path_history+file_in_use): # si el archivo existe, se sobreescribe
                    print(f'{pasos}- Sobreescribiendo el archivo!', end='\n\n')

                    pd.DataFrame(chat_log).T.to_json(path_history+file_in_use)
                    return

                print(f'{pasos}- El archivo del cual se cargó el chat ya no existe!'); pasos+=1
                file_in_use = '' # si el archivo no existe, se limpia la variable file_in_use

            # si no se está usando un archivo o el archivo en uso ya no existe, se guarda en un nuevo archivo
            print(f'{pasos}- Creando un nuevo archivo!', end='\n\n')

            prompt = "Elije un título para la conversación basado en el contexto actual, que NO exceda las 5 palabras."
            response = predict(chat_log[2:] + [{"role": "user", "content": prompt}]).strip('."')
            pd.DataFrame(chat_log).T.to_json(path_history+f'{response.lower()}.json')
    except:
        error('Error, no se pudo guardar el contexto.')


def get_contents_files(extension='.json'):
    print('Se entró en la función get_contents_files():')
    try:
        files_name = [file for file in os.listdir(path_history) if file.endswith(extension)]
        contents = [file.capitalize().replace(extension,'') for file in files_name]

        print(f'1- Se obtuvieron los nombres de los archivos {extension}!',end='\n\n')
        return files_name, contents
    except:
        error('Error, no se encontraron archivos con la extensión especificada.')


def get_content_from_file(file_name):
    print('Se entró en la función get_content_from_file():')
    try:
        content = pd.read_json(path_history+file_name).to_dict()

        print(f'1- Se obtuvo el registro a partir del archivo "{file_name}"!',end='\n\n')
        return [v for v in content.values()]
    except:
        error('Error, no se pudo cargar el contenido del archivo especificado.')


def set_rol(rol):
    global chat_log, actual_rol
    print('Se entró en la función set_rol():')
    chat_log = rols[rol]
    print('1- Se actualizó el registro!')
    actual_rol = rol
    print('2- Se actualizó el rol actual!',end='\n\n')


def get_rol_from_chatlog():
    print('Se entró en la función get_rol_from_chatlog():')
    if not chat_log[0]['content']:
        print('1- Se obtuvo el rol: General assistant 🤖!',end='\n\n')
        return 'General assistant 🤖'

    for key, value in zip(rols.keys(), rols.values()):
        if key == 'General assistant 🤖':
            continue
        if value[0]['content'] == chat_log[0]['content']:
            print(f'1- Se obtuvo el rol: {key}!',end='\n\n')
            return key
    error('Error, no existe el rol!')

def send_hello(msg):
    print('Se entró en la función send_hello():')
    bot.send_message(chat_id=msg.chat.id, text=f'Que bolá Arche 👋. Mi rol actual es: {actual_rol} !')
    print('1- Se envió el mensaje de saludo al chat!')
    bot.pin_chat_message(chat_id=msg.chat.id, message_id=msg.message_id+1)
    print('2- Se fijó el mensaje!',end='\n\n')


# manejar la pulsación del comando \log
@bot.message_handler(commands=['log'])
def show_log(message):
    actual_content = '\n' + '\n'.join(['* ' + item['content'] for item in chat_log[2:] if item['role']=='user'])
    bot.send_message(chat_id=message.chat.id, text=f'El contexto actual es: {actual_content}')


# manejar salida del comando \newchat
@bot.message_handler(commands=['newchat'])
def newchat(message):
    save_content()
    delete_content()
    send_hello(message)
    print()


# manejar la pulsación del comando \load
@bot.message_handler(commands=['load'])
def load_file_content(message):
    _, contents = get_contents_files('.json')

    if not contents:
        bot.send_message(chat_id=message.chat.id, text='No se encontraron otros chats 🤷‍♂️')
    else:
        menu = [[types.InlineKeyboardButton(text = content, callback_data=content.lower())] for content in contents]
        keyboard = types.InlineKeyboardMarkup(menu)
        bot.send_message(chat_id=message.chat.id, text='Elije un contexto para cargar:', reply_markup=keyboard)


# manejar la pulsación del comando \rol
@bot.message_handler(commands=['rol'])
def change_rol(message):
    rol_menu = [[types.InlineKeyboardButton(text = item, callback_data=item.lower())] for item in rols.keys()]
    keyboard = types.InlineKeyboardMarkup(rol_menu)

    bot.send_message(chat_id=message.chat.id, text='Elije un rol para ChatGPT:', reply_markup=keyboard)


@bot.message_handler(content_types=['text'])
def reply_handler(message):
    if message.text in ['q', 'quit', 'Q', 'Quit', 'exit', 'Exit']:
        print('Deteniendo el bot...\n\n')
        bot.stop_bot()
        save_content()
    else:
        chat_log.append({"role": "user", "content": message.text})
        bot.reply_to(message, 'cargando ···')

        response = predict(chat_log)

        bot.send_message(chat_id=message.chat.id, text=response)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id+1)

        chat_log.append({"role": "assistant", "content": response})


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    files_name, contents = get_contents_files('.json')
    call_data = call.data.capitalize()
    z = dict(zip(contents, files_name))

    if call_data in z.keys():
        global chat_log, file_in_use, actual_rol

        chat_log = get_content_from_file(z[call_data])
        actual_rol = get_rol_from_chatlog()
        file_in_use = z[call_data]
        send_hello(call.message)

    elif call_data in rols.keys():
        save_content()
        set_rol(call_data)
        send_hello(call.message)

    print()


bot.polling()
