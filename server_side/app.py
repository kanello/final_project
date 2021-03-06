from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3 
import re
import bcrypt
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token


app = Flask(__name__)
app.config["JWT_SECRET_KEY"]='secret-key'
CORS(app, resources={r"*": {"origins": "*"}})

#create database connection and create user tables
con = sqlite3.connect('belay.db', check_same_thread=False)
cur = con.cursor()
jwt = JWTManager(app)

def check_if_img(text):
    """Reads text. If image url detected, returns the image link
    """

    return re.findall(r'(?:http\:|https\:)?\/\/.*\.(?:png|jpg|jpeg)', text)


#-------------------API ROUTES---------------------
@app.route('/credentials-check', methods=['POST'])
def credentials_check():
    """
    Credentials check. See if user has entered correct info

    Parameters
    request:
        - json object containing {username: username, password: hashed_password}

    Returns
    json object:
        - json string with success message
    """
    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    username =  request.json["username"] 
    password =  request.json["password"] 

    #pass sanitised sql
    cur.execute("select user_password, user_id from users where user_name = ?;", (username, ))
    outcome = cur.fetchone()

    if outcome == None:
        return jsonify({"success":False, "message":'user and pass combo not correct'})

    access_token = create_access_token(identity=outcome[1])
 
    if bcrypt.checkpw(password.encode('utf-8'), outcome[0].encode('utf-8')):

        con.close()

        return jsonify({"success":True, "message":f'Logged in, welcome back {username}', "user":username, "id":outcome[1], "token":access_token})
    con.close()

    return jsonify({"success":False, "message":f'user and pass combo not correct'})

@app.route('/create-user', methods=['POST'])
def create_user():
    """
    Create user

    Parameters
    request:
        - json object containing {username: username, password: hashed_password}

    Returns
    json object:
        - json object containing success or fail message
    """

    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    username =  request.json["username"] 
    password =  request.json["password"]
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    #check that user doesn't exist
    cur.execute("select count(*) from users where user_name = ?;", (username,))
    outcome = cur.fetchone()
    

    #check username is "clear"
    if outcome[0] == 0:

        cur.execute(f"""insert into users (user_name, user_password) values ("{username}", "{hashed.decode('utf-8')}");""")
        
        #need this here for the data to persist, otherwise it gets dumped
        con.commit()

        cur.execute("select user_id from users order by 1 desc limit 1")
        outcome = cur.fetchone()
        access_token = create_access_token(identity=outcome[0])

        con.close()

        return jsonify({"success":True, "message":f'Successfully created {username}', "token":access_token, "id":outcome[0]})

    con.close()
    
    return jsonify({"success":False, "message":f'{username} is taken'})

@app.route('/create-channel', methods=['POST'])
@jwt_required()
def create_channel():
    """
    Create channel

    Parameters
    request:
        - json object containing {channel: channel_name}

    Returns
    json object:
        - json object containing success or fail message
    """
    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    channel_name =  request.json["channel_name"] 
    

    #check that user doesn't exist
    cur.execute("select count(*) from channels where channel_name = ?;", (channel_name, ))
    outcome = cur.fetchone()

    #check channel name is available is "clear"
    if outcome[0] == 0:

        cur.execute(f"""insert into channels (channel_name) values ("{channel_name}");""")
        
        #need this here for the data to persist, otherwise it gets dumped
        con.commit()
        con.close()

        return jsonify({"success":True, "message":f'Successfully created {channel_name}'})
    con.close()
    
    return jsonify({"success":False, "message":f'{channel_name} is taken'})
        
@app.route('/write-message', methods=['POST'])
@jwt_required()
def write_message():
    """
    Write message. Takes the json object passed through, autogenerates an id, timestamp and writes the message to the database, persisting the change.

    Timestamp is generated via the sql query => datetime('now')

    Parameters
    request:
        - json object containing {message: message_body, author_id:author_id, channel_id:channel_id}

    Returns
    json object:
        - json object containing success or fail message
    """
    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    message_body = request.json["message_body"]
    user_id = request.json["user_id"]
    channel_id =  request.json["channel_id"] 
    

    cur.execute(f"insert into messages (message_body, sent_time, user_id, channel_id) values ('{message_body}', datetime('now'), '{user_id}', '{channel_id}');")
    
    #need this here for the data to persist, otherwise it gets dumped
    con.commit()
    con.close()

    return jsonify({"success":True, "message":f'wrote message'})
    
@app.route('/write-reply', methods=['POST'])
@jwt_required()
def write_reply():
    """
    Write a reply to a message. Takes the json object passed through, autogenerates an id, timestamp and writes the reply to the database, persisting the change.

    Timestamp is generated via the sql query => datetime('now')

    Parameters
    request:
        - json object containing 

    Returns
    json object:
        - json object containing success or fail message
    """

    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    reply_body = request.json["reply_body"]
    user_id = request.json["user_id"]
    msg_id =  request.json["msg_id"] 

    
    cur.execute(f"insert into replies (reply_body, sent_time, msg_id, user_id) values ('{reply_body}', datetime('now'), '{msg_id}', '{user_id}');")
    
    #need this here for the data to persist, otherwise it gets dumped
    con.commit()
    con.close()

    return jsonify({"success":True, "message":f'wrote reply'})

@app.route('/get-channels', methods=['GET'])
@jwt_required()
def get_channels():
    """
    Gets all the available channels from the database and returns them as a json object

    Parameters
    None

    Returns
    json_object
        - channels: {channel_id:channel_name}
    """
    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    query = cur.execute("select * from channels order by channel_name asc;")
    channels = []
    for row in query.fetchall():
        new_channel={
            "channel_id":str(row[0]),
            "channel_name":row[1]
        }
        channels.append(new_channel)
        
    con.close()
    return jsonify(channels)

@app.route('/get-channel/<id>', methods=['GET'])
@jwt_required()
def get_channel_name(id):



    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()
    data=""
    query = cur.execute(f'select channel_name from channels where channel_id="{id}"')
    for row in query.fetchall():
        data = row[0]


    con.close()
    
    return jsonify(data)

@app.route('/get-messages/<channel_id>', methods=['GET'])
@jwt_required()
def get_messages(channel_id):
    """
    Gets all the messages and responses for that specific channel

    Parameters
    channel_id
        - channel id from which to grab the messages

    Returns
    json_object
        - channels: {channel_id:channel_name}
    """
    # print(type(channel_id))
    try:
        a = int(channel_id)
    except:
        return ({"response":"undefined channel"})
    

    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    #prepare the query
    query = con.execute("select * from v_messages where channel_id=?;", (channel_id), )


    if query.rowcount == 0:

        return jsonify({"response":"no messages yet"})
    
    
    messages = []
    for row in query.fetchall():
      
        new_message = {"msg_id": str(row[2]), "body":row[3], "author":row[1], "time":row[4], "replies":[], "images":check_if_img(row[3])}
        messages.append(new_message)

    #might have to find a better way of doing this. Nested ain't a good idea    
    for message in messages:
        
        query = con.execute("select * from v_replies_user where msg_id=?;", (message["msg_id"], ))
        
        for row in query.fetchall():
            new_reply={"reply_id":row[4], "user_name":row[0], "reply_body":row[1], "sent_time":row[2]}
            message["replies"].append(new_reply)
    
    con.close()
    
    return jsonify(messages)

@app.route('/get-replies/<message_id>', methods=['GET'])
@jwt_required()
def get_replies(message_id):
    """
    """
    con = sqlite3.connect('belay.db', check_same_thread=False)
    cur = con.cursor()

    #request the database for the replies to the messages given
    query = cur.execute(f'select reply_body, sent_time, user_name from v_replies_user where msg_id="{message_id}"')

    replies = []
    for row in query.fetchall():
        replies.append({"reply_body":row[0], "sent_time":row[1], "author":row[2]})

    con.close()
    
    return jsonify(replies)



if __name__ == '__main__':
    app.run()
