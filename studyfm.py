#coding=utf-8
from __future__ import print_function
import requests
import json

COOKIE = {'dbcl2': '"154580510:2248k2xl9dc"', 'bid': 'kuoU3VSx7Dk', 'fmNlogin': '"y"'}
HEADERS = {"User-Agent": "Paw/2.2.5 check current song(Macintosh; OS X/10.11.1) GCDHTTPRequest"}
PLAYLIST_ENDPOINT = "https://douban.fm/j/v2/playlist"
TOKEN_DELIMITER = "|"
RETRY_COUNT = 20

CHANEL_LIST = {
    'heart': -3,
    'personal': 0,
    'daily': -2,
    'picked': -10,
    'working': 153,
    'resting': 152,
    'Chinese': 1,
    'English': 2,
    'japanese': 17,
    'pop': 194,
    'rock': 7,
    'country': 8,
    'light': 9,
    'jazz': 13,
    'classic': 27,
    'blues': 188,
    'fresh': 76
}

LOOP_OFF_LIST = [
    "AMAZON.NextIntent",
    "AMAZON.CancelIntent",
    "AMAZON.StopIntent",
    "PlayChanelIntent",
]

# ----------------Global variables----------------------------------------------

paused_offset = 0
paused_token = None
current_token = None
current_song = None
queue = []
current_chanel = 0
loop_on = False

# --------------- Helpers that build all of the responses ----------------------

def build_ssml_response(field, field_value, audio_link):
    ssml = "<speak>The song's " + field + "is ";
    if field_value:
        ssml = ssml + field_value
    if audio_link:
        ssml = ssml + "<audio src='" + audio_link + "' />"
    ssml = ssml + "</speak>"
    return {
        "outputSpeech": {
            "type": "SSML",
            "ssml": ssml
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + field,
            'content': "SessionSpeechlet - " + field
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': field
            }
        },
        'shouldEndSession': True
    }
    
def build_speechlet_response(output, title, reprompt_text):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': True
    }
    
def build_audio_stop_response():
    return {
        "directives": [
            {
                "type": "AudioPlayer.Stop"
            }
        ],
        'shouldEndSession': True
    }
    
def build_audio_play_response(play_type, play_behavior, sid, url, offset):
    token = sid + TOKEN_DELIMITER + url
    return {
        "directives": [
            {
                "type": play_type,
                "playBehavior": play_behavior,
                "audioItem": {
                    "stream": {
                        "token": token,
                        "url": url,
                        "offsetInMilliseconds": offset
                    }
                }
            }
        ],
        'shouldEndSession': True
    }

def build_response(response):
    print('---RESPONSE SENT---')
    return {
        'version': '1.0',
        'sessionAttributes': {},
        'response': response
    }
    
# --------------- Functions that control the skill's behavior ------------------

def requests_url(ptype, **data):
    options = {
        'type': ptype,
        'pt': '3.1',
        'channel': current_chanel,
        'pb': '320',
        'from': 'mainsite',
        'r': '',
        'kbps': '320',
        'app_name': 'radio_website',
        'client': 's:mainsite|y:3.0',
        'version': '100'
    }
    if 'sid' in data:
        options['sid'] = data['sid']
    count = 0
    while count < RETRY_COUNT:
        try:
            s = requests.get(PLAYLIST_ENDPOINT, params=options, cookies=COOKIE, headers=HEADERS)
            req_string = s.content.decode('ISO-8859-1')
            req_json = json.loads(req_string)
            if req_json['r'] == 0:
                if 'song' not in req_json or not req_json['song']:
                    print('!!!no song get!!!')
                    return None
                song = req_json['song'][0]
                print('Raw song get' + str(song))
                if song['url'].startswith('http') and not song['url'].startswith('https'):
                    parts = song['url'].split('http', 1)
                    song['url'] = 'https' + parts[1]
                print('Song to reutrn' + str(song))
                global queue
                queue.append(song)
                return song
            count += 1
        except Exception, err:
            print('Request failed')
            print(err)
            break
    return None

def get_first_song():
    song = requests_url('n')
    if song:
        print('---Play Song: ' + song['sid'] + TOKEN_DELIMITER + song['url'])
        return build_response(build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ALL', song['sid'], song['url'], 0))

def get_song(token):
    [sid, url] = token.split(TOKEN_DELIMITER)
    song = requests_url('p', sid=sid)
    if song:
        print('---Enque Song: ' + song['sid'] + TOKEN_DELIMITER + song['url'])
        return build_response(build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ENQUEUED', song['sid'], song['url'], 0))

def pause(pause_request, session): 
    return build_response(build_audio_stop_response())

def resume(resume_request, session):
    if paused_token:
        print('---pause token: ' + paused_token + ' pause offset: ' + str(paused_offset) + '---')
        [sid, url] = paused_token.split(TOKEN_DELIMITER)
        return build_response(build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ALL', sid, url, paused_offset))
    else:
        return get_first_song()

def startover():
    print('startover' + current_token)
    if current_token:
        [sid, url] = current_token.split(TOKEN_DELIMITER)
        return build_response(build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ALL', sid, url, 0))
            
def loopon():
    global loop_on
    loop_on = True
    response = enque_current_song()
    output = 'Ok, Loop on this song'
    speech = build_speechlet_response(output, output, output)
    response['response']['outputSpeech'] = speech['outputSpeech']
    response['response']['reprompt'] = speech['reprompt'] 
    response['response']['card'] = speech['card'] 
    return response

def loopoff():
    global loop_on
    loop_on = False
    response = get_song(current_token)
    output = 'Ok, Loop off this song'
    speech = build_speechlet_response(output, output, output)
    response['response']['outputSpeech'] = speech['outputSpeech']
    response['response']['reprompt'] = speech['reprompt'] 
    response['response']['card'] = speech['card'] 
    return response
    

def skip(skip_request, session):
    if current_token:
        print('---current_token: ' + current_token + '---')
        [sid, url] = current_token.split(TOKEN_DELIMITER)
        song = requests_url('s', sid=sid)
        return build_response(build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ALL', song['sid'], song['url'], 0))
            
def chanel(chanel_request, session):
    if 'Chanel' in chanel_request['slots']:
        chanel = chanel_request['slots']['Chanel']['value']
        global current_chanel
        current_chanel = CHANEL_LIST[chanel]
        return get_first_song()
        
def mark(mark_request, session):
    if 'MarkAction' in mark_request['slots']:
        mark_action = mark_request['slots']['MarkAction']['value']
    if current_token:
        [sid, url] = current_token.split(TOKEN_DELIMITER)
        if mark_action == 'heart':
            output = "OK, I've hearted this song"
            song = requests_url('r', sid=sid)
            response = build_speechlet_response(output, output, "")
        elif mark_action == 'unheart':
            output = "Allright, I've unhearted this song"
            song = requests_url('u', sid=sid)
            response = build_speechlet_response(output, output, "")
        elif mark_action == 'delete':
            output = "No problem, I've deleted this song"
            song = requests_url('b', sid=sid)
            print(str(song))
            response = build_speechlet_response(output, output, "")
            response['directives'] = build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ALL', song['sid'], song['url'], 0)["directives"]
        return build_response(response)

def song_info(info_request, session):
    if 'Info' in info_request['slots']:
        info_field = info_request['slots']['Info']['value']
        print('check current song')
        if current_song:
            info = current_song[info_field]
            print('has current song')
            print(info)
            info_value = None
            info_link = None
            if current_chanel == CHANEL_LIST['English']:
                info_value = info
            elif current_chanel == CHANEL_LIST['Chinese']: 
                info_link = "https://translate.google.com/translate_tts?ie=UTF-8&q=" + info + "&tl=zh-TW&&client=tw-ob"
            response = build_ssml_response(info_field, info_value, info_link)
            return build_response(response)
            
def handle_song_nearly_finish(token):
    if loop_on and current_token:
        return enque_current_song()
    return get_song(token)

def enque_current_song():
    if current_token:
        [sid, url] = current_token.split(TOKEN_DELIMITER)
        return build_response(build_audio_play_response(
            'AudioPlayer.Play', 'REPLACE_ENQUEUED', sid, url, 0))
    
def set_paused_song(audio_request):
    global paused_token
    paused_token = audio_request['token']
    global paused_offset 
    paused_offset = audio_request['offsetInMilliseconds']
    print('---pause token: ' + paused_token + ' pause offset: ' + str(paused_offset) + '---')

def set_current_song(audio_request):
    global current_token
    current_token = audio_request['token']
    global queue
    global current_song
    if len(queue) > 0:
        current_song = queue.pop() 
    print('---current token: ' + current_token)

# --------------- Events ------------------

# Not used for now
def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_first_song()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    print('---Intent Name: ' + intent_name + ' ---')
    if intent_name in LOOP_OFF_LIST:
        global loop_on
        loop_on = False;

    # Dispatch to your skill's intent handlers
    if intent_name == "AMAZON.PauseIntent":
        return pause(intent_request, session)
    elif intent_name == "AMAZON.ResumeIntent":
        return resume(intent_request, session)
    elif intent_name == "AMAZON.NextIntent":
        return skip(intent_request, session)
    elif intent_name == "AMAZON.StartOverIntent":
        return startover()
    elif intent_name == "AMAZON.LoopOnIntent":
        return loopon()
    elif intent_name == "AMAZON.LoopOffIntent":
        return loopoff()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return pause(intent_request, session)
    elif intent_name == "MarkSongIntent":
        return mark(intent, session)
    elif intent_name == "PlayChanelIntent":
        return chanel(intent, session)
    elif intent_name == "SongInfoIntent":
        return song_info(intent, session)
    else:
        raise ValueError("Invalid intent")
    #OTHER INTENT LIKE rate & unrate

def on_playback_request(playback_request):
    request_type = playback_request['type']
    print("----Playback Request---")
    print(json.dumps(playback_request))
    if request_type == 'PlaybackController.NextCommandIssued':
        return skip(playback_request, {})
    elif request_type == "PlaybackController.PlayCommandIssued":
        return resume(playback_request, {})
    elif request_type == "PlaybackController.PreviousCommandIssued":
        return startover()
    
def on_audio_request(audio_request, session):
    request_type = audio_request['type']
    print("---Audio request---")
    if request_type == 'AudioPlayer.PlaybackNearlyFinished':
        return handle_song_nearly_finish(audio_request['token'])
    elif request_type == 'AudioPlayer.PlaybackStopped':
        return set_paused_song(audio_request)
    elif request_type == 'AudioPlayer.PlaybackStarted':
        return set_current_song(audio_request)

def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])
    """
    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")
    
    # audio play request has no session
    #if event['session'] && event['session']['new']:
    #    on_session_started({'requestId': event['request']['requestId']},
    #                       event['session'])
    print('---REQUEST GET---')
    event_type = event['request']['type']
    print('---Request type: ' + event_type)
    if event_type.startswith('PlaybackController'):
        return on_playback_request(event['request'])
    elif event_type.startswith('AudioPlayer'):
        return on_audio_request(event['request'], {})
    elif event_type == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event_type == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event_type == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
    print(str(event))
