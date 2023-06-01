from googleapiclient import discovery
import json
import os

# API key loaded here from `./.env` to PERSPECTIVE_API_KEY
#load_dotenv()
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")

attrs = {
	'TOXICITY': {},
	'SPAM': {}, # “Experimental” attribute: https://developers.perspectiveapi.com/s/about-the-api-attributes-and-languages?language=en_US
	'THREAT': {}
}
client = discovery.build(
	"commentanalyzer",
	"v1alpha1",
	developerKey=PERSPECTIVE_API_KEY,
	discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
	static_discovery=False,
)


comments = [
	'This is an important message from Wells Fargo. Please sign in here to review a suspicious login to your account: https://bit.ly/12345678',
	'This is the FBI. If you do not click this link you will be ARRESTED and put IN JAIL.',
	'We have your granddaughter. We will hurt her unless you pay 28.485 ETH to the address 0xb0d042f70c02630ea30975017e03cb50140f594afc0af717413a12f0a56e3174 in the next 24 hours.',
	'This is the Federal Investigations Department. IRS records show that there are a number of overseas transactionsunder your name, you need to pay the full portion of the transaction fees to the IRS Department, which you never did. You currently owe $5,638.38. Please call us as soon as possible at (415)-555-3437.'
]

def perspective_spam_classify(msg, threshold):
	analyze_request = {
    	'comment': { 'text': msg},
    	'requestedAttributes': attrs
	}
	response = client.comments().analyze(body=analyze_request).execute()
	spam_res = response["attributeScores"]["SPAM"]["summaryScore"]
	spam_prob = spam_res["value"]
	if spam_prob >= threshold:
	    return "spam"
	else:
		return "not spam"


def perspective_spam_prob(msg):
    try:
	    analyze_request = {
    	    'comment': { 'text': msg},
    	    'requestedAttributes': attrs
	    }
	    response = client.comments().analyze(body=analyze_request).execute()
	    spam_res = response["attributeScores"]["SPAM"]["summaryScore"]
	    spam_prob = spam_res["value"]
	    return spam_prob
    except:
        print("perspective API failed")
        return 0

def perspective_threat_prob(msg):
    try:
	    analyze_request = {
    	    'comment': { 'text': msg},
    	    'requestedAttributes': attrs
	    }
	    response = client.comments().analyze(body=analyze_request).execute()
	    threat_res = response["attributeScores"]["THREAT"]["summaryScore"]
	    threat_prob = threat_res["value"]
	    return threat_prob
    except:
        print("perspective API failed")
        return 0


def perspective_sum_classify(msg, threshold, spam_weight, threat_weight):
    denom = spam_weight + threat_weight
    num = perspective_threat_prob(msg) * threat_weight + perspective_spam_prob(msg) * spam_weight
    val = num / denom
    if (num / denom) >= threshold:
        return "spam"
    else:
        return "not spam"

print(perspective_spam_prob(comments[0]))
print(perspective_threat_prob(comments[2]))
for comment in comments:
    print(perspective_sum_classify(comment, threshold=0.4, spam_weight=2, threat_weight=1))
