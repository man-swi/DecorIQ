import streamlit as st
from streamlit_chat import message
from prod_info import products
from helpers import  sleep_me, generate_product_description
from hidden_file2 import find_agruments

print("Main:  Initializing.......\n")

########################### Generating Sessions ###########################


first_call = ("Hello! I am a Furniture Seller Assistant. I interact with customers "
                "and help them buy, explain, book furniture, Track Orders or Cancel Bookings. "
                "How can I assist you today? "
                "Start by saying show me the products")

if 'bot_responses' not in st.session_state:
    st.session_state['bot_responses'] = [first_call]

if 'query_requests' not in st.session_state:
    st.session_state['query_requests'] = []

if 'show_all_products_flag' not in st.session_state:
    st.session_state['show_all_products_flag'] = False

if 'show_one_product_flag' not in st.session_state:
    st.session_state['show_one_product_flag'] = "0"

if 'description' not in st.session_state:
    st.session_state['description'] = dict()

############ Knowing session state

# print(f"Main:{st.session_state['bot_responses']  = } \n\n")
# print(f"Main:{st.session_state['query_requests']  = } \n\n")
# print('reloaded..............\n\n')


############################## Calling AGENT ####################################

from langchain_core.messages import HumanMessage
from utils import agent_executor
config = {"configurable": {"thread_id": "abc123"}}

############################## Designing UI #####################################
# st.title("title",)
col1, col2, col3 = st.columns([0.1,0.8,0.1])

with col1:
    st.write(' ')

with col2:
    st.title("DecorIQ: green[AI-Powered LLM Shopping Agent]")

with col3:
    st.write(' ')

# st.subheader("Seller Agent")

all_image_container = st.container(border=True)
bot_responses_container = st.container(border=True)
query_requests_container = st.container(border=True)
 


with query_requests_container:
    print("Main:  Inside query container............\n")

    query = st.chat_input("QUERY here")

    if query:
        st.write("Main:   Got the query....\n\n")

        with st.spinner("Deciding....."):
            sleep_me()
            
            # Use invoke() for cleaner, more stable execution
            result = agent_executor.invoke({"messages": [HumanMessage(content=query)]}, config)
            
            # Extract final response
            final_messages = result.get("messages", [])
            if final_messages:
                res = final_messages[-1].content
            else:
                res = "I apologize, but I couldn't process your request."

            st.session_state['bot_responses'].append(res)
            st.session_state['query_requests'].append(query)

            # Check which tools were called by examining the message history
            show_all_prod = False
            show_one_prod = False
            process_order_called = False
            
            for msg in final_messages:
                if hasattr(msg, 'tool_calls'):
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', '')
                        if tool_name == "show_all_products":
                            show_all_prod = True
                        elif tool_name == "get_product_details" and isinstance(tool_call, dict):
                            show_one_prod = True
                            product_id = tool_call.get('args', {}).get('product_id', "0")
                            st.session_state['show_one_product_flag'] = product_id
                        elif tool_name == "process_order":
                            process_order_called = True
            
            if show_all_prod:
                st.session_state['show_all_products_flag'] = True
            
            print(f"Main: Tools called - show_all_products={show_all_prod}, get_product_details={show_one_prod}, process_order={process_order_called}\n") 

with bot_responses_container:
    print("Main:  Inside Bot container.........\n")

    if st.session_state['bot_responses']:
        count=0
        while count < len(st.session_state['bot_responses']) :
            message(st.session_state['bot_responses'][count] , key= 'bot_'+ str(count))
            if count == (len(st.session_state['bot_responses']) - 1):
                break

            if st.session_state["query_requests"]:
                message(st.session_state['query_requests'][count], 
                        is_user=True, key= 'user_'+ str(count))
            count += 1

if st.session_state['show_all_products_flag']:
    # st.write("Main: show all flags was found ")

    with all_image_container:
        row1 = st.columns(3)
        row2 = st.columns(3)
        row3 = st.columns(4)

        for i, col in enumerate(row1 + row2 + row3):
            price = products[str(i+1)]["MRP"]
            path = products[str(i+1)]["location"]

            tile = col.container(height=220)
            tile.markdown(f"{i+1}.  MRP Rs.{price}")
            tile.image(path)

if st.session_state['show_one_product_flag'] != "0":
    # st.write("Main: one flag was not 0")
    one_image_container = st.container(border=True, height= 300)

    prod_id = st.session_state['show_one_product_flag']

    path = products[prod_id]["location"]
    # sleep_me()
    if prod_id not in st.session_state['description']:
        st.session_state['description'][prod_id] = generate_product_description(prod_id)
    
    creative_description = st.session_state['description'][prod_id]

    with one_image_container:
        img_col, des_col = st.columns([1,2])
        with img_col:
            st.image(path)

        with des_col:
            st.markdown(creative_description)
