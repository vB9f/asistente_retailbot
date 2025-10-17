import os
import re
import openai
import streamlit as st
import smtplib
from email.message import EmailMessage

# Claves y archivos
with open("clave_api.txt") as archivo:
    openai.api_key = archivo.readline().strip()

with open("productos_ropa.csv") as archivo:
    producto_csv = archivo.read()

with open("reglas.txt") as archivo:
    reglas = archivo.read()

with open("correo.txt") as archivo:
    correo = archivo.read()

with open("clave_correo.txt") as archivo:
    clave_correo = archivo.read()

# Personalización del estilo
BACKGROUND_COLOR = '#3F192F'

st.markdown(f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, {BACKGROUND_COLOR}, #1e1e2d);
        color: #ffffff;
    }}
    .st-emotion-cache-1cypcdb {{
        background-color: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
    }}
    .st-emotion-cache-1ujx7c9 {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #1f4068;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 20px;
    }}
    .st-emotion-cache-1ujx7c9 img {{
        display: none;
    }}
    .st-emotion-cache-121p2k {{
        background-color: #1f4068;
        border-radius: 15px;
        color: #ffffff;
        padding: 15px;
        max-width: 80%;
        align-self: flex-end;
    }}
    .st-emotion-cache-1ujx7c9 + .st-emotion-cache-1y4qf8o {{
        background-color: #162447;
        border-radius: 15px;
        color: #ffffff;
        padding: 15px;
        max-width: 80%;
        align-self: flex-start;
    }}
</style>
""", unsafe_allow_html=True)

# Título de aplicación
st.title("Asistente - RetailBot 🛍️🏪")

# Contexto en sesión de Streamlit
if "contexto" not in st.session_state:
    st.session_state.contexto = [
        {'role': 'system', 'content': f"{reglas} {producto_csv}"}
    ]

if "esperando_email" not in st.session_state:
    st.session_state.esperando_email = False

if "usuario_email_enviado" not in st.session_state:
    st.session_state.usuario_email_enviado = False

# Función - Enviar mensajes al modelo
def enviar_mensajes(messages, model="gpt-4", temperature=0.7):
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content

# Función - Enviar correo a usuario
def enviar_correo(destinatario, asunto, cuerpo):
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = correo
    msg['To'] = destinatario
    msg.set_content(cuerpo)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(correo, clave_correo)
            smtp.send_message(msg)
            return True
    except Exception as e:
        st.error(f"Error al enviar el correo: {e}")
        return False

# Interacción - Agente-Usuario
for chat in st.session_state.contexto[1:]:
    with st.chat_message(chat['role']):
        st.markdown(chat['content'])

if prompt := st.chat_input("Consulta sobre nuestros productos a RetailBot"):
    st.session_state.contexto.append({'role': 'user', 'content': prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Pensando..."):
        respuesta_agente = ""

        if st.session_state.esperando_email:
            usuario_email = prompt
            
            if re.match(r"[^@]+@[^@]+\.[^@]+", usuario_email):
                st.session_state.esperando_email = False
                
                respuesta_resumen_agente = enviar_mensajes(st.session_state.contexto)
                
                patron_resumen = r"Producto:.*?(?:Talla:.*?)?(?:Color:.*?)?(?:Método de pago:.*?)?(?:Total:.*?$)"
                resumen_encontrado = re.search(patron_resumen, respuesta_resumen_agente, re.DOTALL)
                
                if resumen_encontrado:
                    resumen_pedido = resumen_encontrado.group(0)
                else:
                    resumen_pedido = "No se pudo generar el resumen del pedido."
                
                # Ejecución de envío de correo
                asunto = "Detalles de tu Pedido en RetailBot"
                if enviar_correo(usuario_email, asunto, resumen_pedido):
                    st.success("Correo enviado exitosamente.")
                else:
                    st.warning("Hubo un problema al enviar el correo.")

                respuesta_agente = "¡Muchas gracias! Los detalles de tu compra fueron enviados a tu correo."
                st.session_state.contexto.append({'role': 'assistant', 'content': respuesta_agente})

            else:
                respuesta_agente = "La dirección de correo electrónico no es válida. Por favor, inténtalo de nuevo."
                st.session_state.contexto.append({'role': 'assistant', 'content': respuesta_agente})
                
        else:
            # Comportamiento estándar del chatbot
            respuesta_agente = enviar_mensajes(st.session_state.contexto)
            
            # Verificar - respuesta contiene marcador secreto
            if "[MARCADOR_CORREO_EMAIL]" in respuesta_agente:
                st.session_state.esperando_email = True
                # Removemos el marcador para que no se muestre al usuario
                respuesta_agente = respuesta_agente.replace("[MARCADOR_CORREO_EMAIL]", "").strip()
            
            st.session_state.contexto.append({'role': 'assistant', 'content': respuesta_agente})
    
    with st.chat_message("assistant"):
        st.markdown(respuesta_agente)
    st.rerun()