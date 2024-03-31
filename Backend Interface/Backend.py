from flask import Flask, render_template, request, url_for, redirect, flash
from markupsafe import escape
import cohere
import random


co = cohere.Client('kRVV3cOMjnoTO4gCRDKxb1imS0qlLw0EKnmilBuL')
question_answers = []

num_shot = 2
preset_drug_questions = {"whatis": "What is placeholder_medname?",
                         "howdoes": "How does placeholder_medname work?",
                         "isitworking": "How do I know whether placeholder_medname is working?",
                         "sideeffects": "What are the side effects of placeholder_medname?",
                         "placeholder": "placeholder_medname"}

preset_questions_toprint = {"whatis": "What is my prescription drug?",
                         "howdoes": "How does my prescription drug work?",
                         "isitworking": "How do I know whether my prescription drug is working?",
                         "sideeffects": "What are the side effects of my prescription drug?"}

primers_dataset = {"whatis_easy": ["Q: What is ibuprofen?\nA: Ibuprofen is a drug that helps relief pain.",
                                   "Q: What is aspirin?\nA: Aspirin is an anti-inflammatory drug.",
                                   "Q:What is Ozempic?\nA: Ozempic is a single use injection pen for adults with type 2 diabetes mellitus."],
                   "whatis_complex": ["Q: What is ibuprofen?\nA: Ibuprofen is a non-steroidal anti-inflammatory drug that eases mild to moderate pain.",
                                      "Q: What is aspirin?\nA: Aspirin is a salicylate used to treat pain, fever, inflammation, migraines that has both anti-inflammatory and antipyretic effects.",
                                      "Q: What is Ozempic?\nA: Ozempic is a pre-filled, disposable, single-patient-use injection pen used along with diet and exercise to improve blood sugar control in adults with type 2 diabetes mellitus."],
                   "howdoes_easy": ["Q: How does Prozac work?\nA: Prozac helps the brain maintain normal levels of the happy hormone called serotonin.",
                                    "Q: How does Metformin work?\nA: Metformin works by reducing the amount of sugar absorbed by the intestines to help keep blood sugar levels in check.",
                                    "Q: How does Lyrica work?\nA: We are not sure, but research suggests calms down overexcited nerves, thus alleviating pain sensations."],
                   "howdoes_complex": ["Q: How does Prozac work?\nA: Prozac is a selective serotonin reuptake inhibitor (SSRI), meaning that it reduces the brain’s capacity to reabsorb released serotonin neurotransmitters. This allows the neuroreceptors to receive serotonin and fire neurons that produce the feeling of happiness.",
                                       "Q: How does Metformin work?\nA: Metformin works by decreasing the amount of blood sugar that the liver produces and that the intestines or stomach absorb to restore the body’s insulin resistance and regulate blood sugar levels.",
                                       "Q: How does Wegovy work?\nA: Wegovy is a human glucagon-like peptide-1 that mimics the action of GLP-1 produced naturally mainly by the gut. This peptide targets the area of the brain that helps to control appetite. It also slows how quickly the stomach empties, which makes you feel fuller for longer. Wegovy also enhances the release of insulin in response to blood sugar to reduce blood sugar spikes."],
                   "isitworking_easy": ["Q: How do I know whether Doxycycline is working?\nA: The symptoms related to an infection should be reduced after a few days. A doctor can monitor your infection after the treatment to make sure it is resolved.",
                                       "Q: How do I know whether Xanax is working?\nA: A few hours after taking Xanax, you should already feel less anxious and less tense. It could also make you sleepy, especially if taken at night.",
                                       "Q: How do I know whether Cyclobenzaprine is working?\nA: In most cases, you should feel your muscles relax within an hour."],
                   "isitworking_complex": ["Q: How do I know whether Doxycycline is working?\nA: Symptoms brought on by bacterial infection should start subsiding after approximately 3 days of doxycycline treatment. The state of the infection can be confirmed by a doctor after completing the full course of doxycycline. If taken to prevent malaria, there should not be any perceivable changes.",
                                       "Q: How do I know whether Xanax is working?\nA: Feelings of panic and anxiety should subside one or two hours after taking the prescribed dose. The muscles generally are more relaxed and you could experience feelings of drowsiness, especially if taken at night. The effects should be mild if taking the recommended dose.",
                                       "Q: How do I know whether Cyclobenzaprine is working?\nA: You should start feeling less muscle spasm pain within an hour, but full therapeutic affects might take up to 7 days. This relief shouldn't come with any interference of your muscle function."],
                   "sideeffects_easy": ["Q: What are the side effects of Dexedrine?\nA: Dexedrine can induce stomach problems, nausea, headaches, nervousness and dry mouth. It could also slightly increase your blood pressure. You could also have trouble sleeping and be more irritable.",
                                       "Q: What are the side effects of Hydrocodone Bitartrate?\nA: When first starting taking this drug, you could feel nauseated, fatigued, constipated, and light-headed. Vomiting is also common.",
                                       "Q: What are the side effects of Accutane?\nA: Common side effects you could experience are dryness of the skin, eyes, and nose, itchiness, joint pain, and slight vision problems."],
                   "sideeffects_complex": ["Q: What are the side effects of Dexedrine?\nA: Dexedrine can induce stomach aches, loss of appetite, nausea, headaches, nervousness, diarrhea and dry mouth. It could also slightly increase your blood pressure. It can also make you restless, irritable and make it harder to sleep. You might also have a slightly higher blood pressure than usual. The effect should stay the same or improve over time.",
                                       "Q: What are the side effects of Hydrocodone Bitartrate?\nA: Common normal side effects include dizziness, nausea, fatigue/drowsiness, constipation, and vomiting. These should subside after taking the drug for a while since your body will adapt to the drug.",
                                       "Q: What are the side effects of Lyrica?\nA: While taking Lyrica, you may experience dizziness, dry mouth, drowsiness, difficulty concentrating, constipation, and weight gain. More serious side effects include swelling of extremities and blurred vision."]
                   }

#Helper function
def fill_question(question, placeholder, medname):
    return question.replace(placeholder, medname)


def make_prompt(question_type, primer_data, query_drug, answer_type, num_shot=2):
    """
          question_type is one of ["whatis", "howdoes", "isitworking", "sideeffects"]
          query_drug = specific drug patient wants to ask about
          num_shot = # primers to add
          answer_type = easy/complex
          """
    if num_shot < 0:
        raise Exception("Invalid num_shot (negative)")
    else:
        prompt = ""
        # append primers
        randomized_index = [i for i in range(len(primer_data[question_type + "_" + answer_type]))]
        random.shuffle(randomized_index)
        for i in range(num_shot):
            prompt = prompt + primer_data[question_type + "_" + answer_type][randomized_index[i]]
            prompt = prompt + "\n"
        # append actual query
        prompt = prompt + "Q: " + fill_question(preset_drug_questions[question_type],
                                                preset_drug_questions["placeholder"], query_drug)
        prompt = prompt + "\nA:"
        #print(prompt)
        return prompt


def generate(question_type, drug_inquiry, output_style):
    response = co.generate(
    model='xlarge',
    prompt=make_prompt(question_type, primers_dataset, drug_inquiry, output_style, num_shot),
    max_tokens=80,
    temperature=0.2,
    k=0,
    p=0.15,
    frequency_penalty=0,
    presence_penalty=0,
    stop_sequences=[".\n"],
    return_likelihoods='NONE')
    return response.generations[0].text


app = Flask(__name__)

@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/about/')
def about():
    return '<h3>This is a Flask web application.</h3>'


@app.route('/capitalize/<word>/')
def capitalize(word):
    return '<h1>{}</h1>'.format(escape(word.capitalize()))


@app.route('/amiok/<fullPatientInfos>')
def display(fullPatientInfos):
    patientInfos = escape(fullPatientInfos).split(':')
    return render_template('index.html', fullInfos=escape(fullPatientInfos),
                           patientName=patientInfos[0], doctorName=patientInfos[1],
                           Symptoms=patientInfos[2], Diagnosis=patientInfos[3],
                           Prescription=patientInfos[4])



@app.route('/form/<fullPatientInfos>',  methods=('GET', 'POST'))
def form(fullPatientInfos):
    print(question_answers)
    conversation = 'Start conversation... \n'
    #print(generate("whatis", "Meth", "complex"))
    patientInfos = escape(fullPatientInfos).split(':')
    if request.method == 'POST':
        print(request.form)
        print(request.form['question'])
        print(request.form['question_type'])
        answer = ""
        if 'q_type' in request.form.keys():
            #one of the buttons were chosen
            q_type = request.form['q_type']
            inquired_drug = patientInfos[4]
            answer_type = request.form['question_type']
            answer = generate(q_type, inquired_drug, answer_type)
            question_answers.append((preset_questions_toprint[q_type], answer))
        else:
            #freeform question
            answer = co.generate(
                            model='xlarge',
                            prompt=request.form['question'],
                            max_tokens=80,
                            temperature=0.2,
                            k=0,
                            p=0.15,
                            frequency_penalty=0,
                            presence_penalty=0,
                            stop_sequences=[".\n"],
                            return_likelihoods='NONE'
                        ).generations[0].text
            question_answers.append((request.form['question'], answer))
        #for qa in question_answers:
        #    conversation = conversation + qa[0] + '\n' + qa[1] + '\n'

    return render_template('form.html',
                           patientName=patientInfos[0], doctorName=patientInfos[1],
                           Symptoms=patientInfos[2], Diagnosis=patientInfos[3],
                           Prescription=patientInfos[4], question_answers=question_answers)

@app.route('/data/', methods=['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is accessed directly. Try going to '/form' to submit form"
    if request.method == 'POST':
        form_data = request.form
        return render_template('data.html', form_data=form_data)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
