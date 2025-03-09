from flask import Flask, render_template, request, jsonify
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, config_list_from_json
import uuid
import threading
from email_service import EmailService 
import config

app = Flask(__name__)

agents = []
groupchat_manager = None
chat_messages = []
chat_in_progress = False

config_list = config_list_from_json(env_or_file=config.CONFIG_JSON_PATH)
email_service = EmailService()

@app.route('/')
def index():
    return render_template('index.html')

def record_message(sender, recipient, message):
    global chat_messages
    message_text = message.get('content', message) if isinstance(message, dict) else message
    
    message_data = {
        'sender': sender.name,
        'recipient': recipient.name,
        'message': message_text,
        'timestamp': str(uuid.uuid4())
    }
    print(f"Message recorded: {message_data['sender']} -> {message_data['recipient']}: {message_text[:50]}...")
    chat_messages.append(message_data)
    return False

def print_messages(recipient, messages, sender, config):
    if "callback" in config and config["callback"] is not None:
        callback = config["callback"]

        message_content = messages[-1].get('content', str(messages[-1]))
        callback(sender, recipient, message_content)
    print(f"Messages sent to: {recipient.name} | num messages: {len(messages)}")
    return False, None

@app.route('/add_agent', methods=['POST'])
def add_agent():
    data = request.form.to_dict()
    agent_name = data.get('agent_name')
    system_prompt = data.get('system_prompt')
    agent_type = data.get('agent_type')
    agent_id = str(uuid.uuid4())[:8] 
    
    print(f"{agent_type} agent added: {agent_name}")
    print(f"System prompt: {system_prompt}, type: {type(system_prompt)}")
    print(f"Agent ID: {agent_id}")
    print(f"Config list: {config_list}")

    
    if agent_type == 'UserProxyAgent':
        agent = UserProxyAgent(
            name=agent_name,
            system_message=system_prompt,
            human_input_mode="NEVER",
            code_execution_config={
                "work_dir": config.WORK_DIR,
                "use_docker": config.USE_DOCKER, 
            },
        )
    else:
        agent = AssistantAgent(
            name=agent_name,
            system_message=system_prompt,
            llm_config={"config_list": config_list},
        )
    
    agents.append(agent)
    print(f'Added agent: {agent_name}')
    
    return jsonify({
        'status': 'Agent added successfully',
        'agent': {
            'id': agent_id,
            'name': agent_name,
            'type': agent_type,
            'system_prompt': system_prompt
        }
    })

@app.route('/remove_agent', methods=['POST'])
def remove_agent():
    agent_index = int(request.form.get('agent_index'))
    if 0 <= agent_index < len(agents):
        removed_agent = agents.pop(agent_index)
        return jsonify({'status': f'Agent {removed_agent.name} removed successfully'})
    return jsonify({'status': 'Invalid agent index'})

@app.route('/start_chat', methods=['POST'])
def start_chat():
    global groupchat_manager, chat_messages, chat_in_progress
    
    if chat_in_progress:
        return jsonify({'status': 'Chat already in progress'})
    
    chat_messages = []
    
    initial_message = request.form.get('initial_message')
    max_rounds = int(request.form.get('max_rounds', config.CHAT_MAX_ROUNDS))  
    
    if not agents:
        return jsonify({'status': 'Error: No agents added yet'})
    
    for agent in agents:
        if hasattr(agent, 'register_reply'):
            agent.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages,
                config={"callback": record_message}
            )
    print("Agents: ", agents)
    groupchat = GroupChat(agents=agents, messages=[], max_round=max_rounds)
    
    groupchat_manager = GroupChatManager(
        groupchat=groupchat, 
        llm_config={"config_list": config_list}
    )
    
    user_proxies = [agent for agent in agents if isinstance(agent, UserProxyAgent)]
    if not user_proxies:
        temp_user = UserProxyAgent(
            name="TempUser",
            system_message="Temporary user to start the conversation",
            human_input_mode="NEVER"
        )
        temp_user.register_reply(
            [AssistantAgent, None],
            reply_func=print_messages,
            config={"callback": record_message}
        )
        agents.append(temp_user)
        user_proxy = temp_user
    else:
        user_proxy = user_proxies[0]
    
    chat_messages.append({
        'sender': 'User',
        'recipient': 'GroupChat',
        'message': initial_message,
        'timestamp': str(uuid.uuid4())
    })
    
    def run_chat():
        global chat_messages, chat_in_progress
        try:
            chat_in_progress = True
            print("Starting chat with initial message:", initial_message)
            
            user_proxy.initiate_chat(
                groupchat_manager, 
                message=initial_message
            )
            
            print("Chat completed. Total messages captured:", len(chat_messages))
        except Exception as e:
            print(f"Error in chat thread: {e}")
            import traceback
            traceback.print_exc()
        finally:
            chat_in_progress = False
    
    chat_thread = threading.Thread(target=run_chat)
    chat_thread.daemon = True
    chat_thread.start()
    
    return jsonify({'status': 'Chat started'})

@app.route('/get_responses', methods=['GET'])
def get_responses():
    return jsonify(chat_messages)

@app.route('/debug', methods=['GET'])
def debug():
    global groupchat_manager, chat_messages, agents, chat_in_progress
    
    agent_info = []
    for i, agent in enumerate(agents):
        agent_info.append({
            'index': i,
            'name': agent.name,
            'type': agent.__class__.__name__,
            'human_input_mode': getattr(agent, 'human_input_mode', 'N/A')
        })
    
    return jsonify({
        'agents': agent_info,
        'message_count': len(chat_messages),
        'chat_in_progress': chat_in_progress,
        'has_groupchat_manager': groupchat_manager is not None,
        'max_round': getattr(groupchat_manager.groupchat, 'max_round', 'N/A') if groupchat_manager else 'N/A'
    })

@app.route('/reset', methods=['POST'])
def reset():
    global agents, groupchat_manager, chat_messages, chat_in_progress
    
    agents = []
    groupchat_manager = None
    chat_messages = []
    chat_in_progress = False
    
    return jsonify({'status': 'All agents and chat history reset successfully'})

@app.route('/chat_status', methods=['GET'])
def chat_status():
    return jsonify({
        'in_progress': chat_in_progress,
        'message_count': len(chat_messages)
    })

@app.route('/send_emails', methods=['POST'])
def send_emails():
    data = request.json
    emails = data.get('emails', [])
    summary = data.get('summary', '')
    
    if not emails:
        return jsonify({"status": "Error: No email addresses provided", "success": False})
        
    if not summary:
        return jsonify({"status": "Error: No recipient summary provided", "success": False})
    
    result = email_service.send_bulk_emails_async(emails, summary)
    return jsonify(result)

@app.route('/email_status', methods=['GET'])
def email_status():
    status = email_service.get_email_status()
    return jsonify(status)


if __name__ == '__main__':
    app.run(debug=True)


##################################################################

# import autogen

# def main():
#     config_list = autogen.config_list_from_json(env_or_file='config.json')
#     planner = autogen.AssistantAgent(
#         name="hospital_planner",
#         system_message="""
#         Hospital administrator.

#         Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval.
#         The plan may involve an epidemiologist who defines the patient criteria to solve target outreach.
#         The data analyst who can write code and an executor who will run the code to output a list of patients.
#         An outreach assistant who can take the list of patients and write personalized messages to them.
#         Explain the plan first. Be clear which step is performed by the epidemiologist, data analyst, executor
#         and outreach admin.
#         """,
#         llm_config={"config_list":config_list},
#     )

#     epidemiologist = autogen.AssistantAgent(
#         name="epidemiologist",
#         system_message="""
#         Epidemiologist. You are an expert in the healthcare system. You can help the planner to define which patients 
#         that should receive outreach. Define the criteria based on their demographics, medications and past conditions. 
#         When you have the criteria defined pass these onto the data analyst to write and execute code to search within
#         a FHIR R4 API server for patients that match the criteria. 
#         """,
#         llm_config={"config_list":config_list},
#     )
#     user = autogen.UserProxyAgent(name="user_proxy",system_message="A human admin who will define the condition that the hospital planner needs to screen for",human_input_mode="NEVER",code_execution_config={"work_dir": "groupchat","use_docker": False},)
#     agents = [user,epidemiologist,planner]
#     groupchat = autogen.GroupChat(agents=agents, messages=[], max_round=10)
#     groupchat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})
#     user.initiate_chat(groupchat_manager,message="I want a plan to Contact all the patients that need a colonoscopy screening where the data can be fetched from  FHIR API server URL is https://hapi.fhir.org/baseR4/")
# if __name__ == "__main__" :
#     main()

