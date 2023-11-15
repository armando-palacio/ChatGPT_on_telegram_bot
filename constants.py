from pathlib import Path

DIR_FILE_PATH = Path(__file__).parent
PATH_HISTORY = DIR_FILE_PATH / 'chats-history'

DEFAULT_ROLE = 'Python coding 🐍'

ROLES = {
    'General assistant 🤖': [{"role":"user","content":""},{"role":"assistant","content":""}],
    'Python coding 🐍':[{"role": "user", "content": "Como aspirante a programador en Python, me gustaría que me proporciones consejos y recursos para mejorar mis habilidades de programación en este lenguaje. Me gustaría conocer las mejores prácticas, técnicas de depuración, manejo de excepciones, gestión de datos, uso de bibliotecas y cualquier otra habilidad que me pueda ayudar a mejorar como programador en Python. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus consejos en la práctica. Si entendiste devolveme un ok."},
        {"role": "assistant", "content": f"ok"}],
    'Optical communication ing. 🛰':[{"role": "user", "content": "Como profesional en el campo de las comunicaciones ópticas satelitales, me gustaría que me proporciones una visión general de los principales desafíos y oportunidades en este campo. Me gustaría conocer las tecnologías más recientes, la normativa y las tendencias actuales en las comunicaciones ópticas satelitales. Por favor, proporciona información detallada y ejemplos específicos para que pueda entender mejor cómo aplicar tus conocimientos en la práctica y desarrollar mi carrera en este campo. Si entendiste devolveme un ok."},
        {"role": "assistant", "content": f"ok"}],
}

