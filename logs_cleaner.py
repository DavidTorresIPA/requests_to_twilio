import sys
import pandas as pd
import ftfy
import json


def get_question_code(questions_dict, message):
    
 #The following message identification part should be done for EVERY question that has {{changing_variables}} inside, because the message will not be the same in json and in the message log.
    #Message will have real names instead of {{flow.data.name}}. If thats the case, identify with a part of the message that doesn't change. Remember your question identification must be unique.
    #the code message[-5:] is the last 5 characteres of message. The code message[:5] is the first 5 characteres of message. 
    if message[-132:]=='La encuesta le tomará 5 minutos y estará disponible por las próximas 24 horas. Para continuar con la encuesta, por favor responda SI':
        message = questions_dict['intro1'] 
    if message[-190:]=='Esta es una encuesta de seguimiento de 5 minutos, para la cual usted nos autorizó contactarlo(a). Le recordamos que estará disponible durante 24 horas. Para continuar, por favor responda SI.':
        message = questions_dict['intro2']  
    if message [-164:]=='Le recordamos que nuestra encuesta corta, para la cual usted nos autorizó contactarlo(a), estará disponible durante 24 horas. Para continuar, por favor responda SI.':
        message = questions_dict['intro3']
    if message [-148:]=='humansubjects@poverty-action.org.  Si desea omitir alguna pregunta responda "OMITIR".  Para continuar responda "SI". De lo contrario, responda "NO".':
        message = questions_dict['incentivo']
    if message[:9]=='¿Es usted':
        message = questions_dict['contact_confirmation']
    if message[:15]=='¿Usted conoce a':
        message = questions_dict['known_confirm'] 
    if message[:14]=='¿Podría darnos':
        message = questions_dict['known_wpp_phone']
    if message[:25]=='¿Conoce algún otro número':
        message=questions_dict['known_call_phone']
    if message[:15]=='¿Todavía reside':
        message = questions_dict['city_confirm']
    if message[:26]=='Para confirmar: ¿la ciudad':
        message = questions_dict['city_other_confirm']
    if message[:20]=='¿Además del telefono':
        message = questions_dict['phone_2']
    if message[:20]=='¿Además del teléfono':
        message = questions_dict['phone_2']
    if message[-16:]=='no está buscando':
        message = questions_dict['lab_1']
    if message[:27]=='Para confirmar: ¿su ingreso':
        message = questions_dict['lab_8']
    for q_code, q_message in questions_dict.items():
        if q_message == message:
            return q_code

    return None
def get_question_message(questions_dict, question_code):

    if question_code in questions_dict:
        return questions_dict[question_code]
    else:
        print(f'Couldnt find question message for {question_code}')
        return None


def clean_raw_data_df(raw_data_df):
    #Encode to utf-8
    raw_data_df['Body'] = raw_data_df['Body'].astype(str).apply(lambda x: ftfy.fix_text(x))

    return raw_data_df

def load_questions_dict(questions_json_path, questions_to_consider):

    filtered_questions_dict = {}

    with open(questions_json_path, encoding="utf8") as questions_json_file:
        questions_dict = json.load(questions_json_file)

        flow_states = questions_dict['states']
        for flow_state in flow_states:
            if flow_state['name'] in questions_to_consider:
                #PENDING: Add some vaidations that properites.body exist
                filtered_questions_dict[flow_state['name']] = ftfy.fix_text(flow_state['properties']['body'])

    return filtered_questions_dict

def create_clean_report(raw_data_path, questions_json_path, questions_to_consider, twilio_number):

    raw_data_df = clean_raw_data_df(pd.read_excel(raw_data_path))
    questions_dict = load_questions_dict(questions_json_path, questions_to_consider)

    #Get list of phone_numbers
    phone_numbers = raw_data_df['From'].unique().tolist()

    #Remove twilio_number from phone_numbers
    phone_numbers.remove(twilio_number)

    #Track of rows of report
    report_rows = []

    for phone_number_index, phone_number in enumerate(phone_numbers):

        #Filter data to only messages sent to this sender or sent by this sender
        phone_number_df = raw_data_df[(raw_data_df['To'] == phone_number) | (raw_data_df['From'] == phone_number)]

        #Reset index to facilitate iteration
        phone_number_df.reset_index(inplace=True)

        #Now we will traverse data related to this phone number buttom to top to reconstruct the conversation
        #Keep record of last seen question code
        last_question_code = None

        #Keep record of question and its answer. Dict will help given that some questions will be asked more than once (when there are errors), so we can override them

        #First lets create empty dict with all keys, cause we want them all in the .csv output as columns
        question_to_answer = {}
        for key in 'number','date':
            question_to_answer[key]=''
        for q in questions_to_consider:
            question_to_answer[q]=''

        #Start filling up json
        question_to_answer['number']=phone_number

        for index, row in phone_number_df[::-1].iterrows():
            sender = row['From']
            message = row['Body']
            date = row['SentDate']
            question_to_answer['date']=date

            message_from_twilio = True if sender==twilio_number else False

            if message_from_twilio:
                this_question_code = get_question_code(questions_dict, message)
                if this_question_code is not None:
                    last_question_code = this_question_code
            else:
                last_question_message = get_question_message(questions_dict, last_question_code)
                question_to_answer[last_question_code] = message


        report_rows.append(question_to_answer)

    report_df = pd.DataFrame(report_rows)
    print(report_df)
    #Export
    report_df.to_csv('clean_log.csv', index=False)


if __name__=='__main__':
    #Pending: include some arguments validation
    raw_data_path = sys.argv[1]
    questions_json_path = sys.argv[2]
    questions_to_consider = sys.argv[3].split(',')
    twilio_number = sys.argv[4]
    create_clean_report(raw_data_path, questions_json_path, questions_to_consider, twilio_number)