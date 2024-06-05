"""
Download the pan12 dataset before using
"""
import os
from bs4 import BeautifulSoup

def read_xml_file(file_path):
    """Read the XML file containing the training corpus."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def fetch_list(file_path):
    """Read the list of sexual predators from a text file."""
    predators = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            predators.append(line.strip())
    return predators

def separate_conversations_by_predators(soup, predators):
    """Separate conversations by whether they contain a message from a predator."""
    convs_with_predators = []
    convs_without_predators = []

    for conversation in soup.find_all('conversation'):
        contains_predator = False
        for message in conversation.find_all('message'):
            author = message.find('author').text.strip()
            if author in predators:
                contains_predator = True
                break

        if contains_predator:
            convs_with_predators.append(conversation)
        else:
            convs_without_predators.append(conversation)

    return convs_with_predators, convs_without_predators

def write_conversations_to_files(convs_with_predators, convs_without_predators):
    """Write each conversation to a separate text file."""
    os.makedirs('predatory', exist_ok=True)
    os.makedirs('not_predatory', exist_ok=True)

    # Write conversations with predators
    for conv in convs_with_predators:
        conv_id = conv['id']
        filename = os.path.join('predatory', f'{conv_id}.txt')
        with open(filename, 'w', encoding='utf-8') as file:
            for message in conv.find_all('message'):
                author = message.find('author').text.strip()
                text = message.find('text').text.strip()
                file.write(f'Author: {author}\nText: {text}\n\n')
        print(f'Predatory conversation {conv_id} written to {filename}')

    # Write conversations without predators
    for conv in convs_without_predators:
        conv_id = conv['id']
        filename = os.path.join('not_predatory', f'{conv_id}.txt')
        messages = conv.find_all('message')
        if len(messages) > 10:
            with open(filename, 'w', encoding='utf-8') as file:
                for message in messages:
                    author = message.find('author').text.strip()
                    text = message.find('text').text.strip()
                    file.write(f'Author: {author}\nText: {text}\n\n')
            print(f'Not predatory conversation {conv_id} written to {filename}')

def process_training_corpus():
    """Main function to process the training corpus."""
    training_corpus_file_path = 'pan12/pan12-sexual-predator-identification-training-corpus-2012-05-01/pan12-sexual-predator-identification-training-corpus-2012-05-17.xml'
    predators_txt_file_path = 'pan12/pan12-sexual-predator-identification-training-corpus-2012-05-01/pan12-sexual-predator-identification-training-corpus-predators-2012-05-01.txt'

    xml_content = read_xml_file(training_corpus_file_path)
    soup = BeautifulSoup(xml_content, 'xml')

    predators = fetch_list(predators_txt_file_path)

    convs_with_predators, convs_without_predators = separate_conversations_by_predators(soup, predators)

    write_conversations_to_files(convs_with_predators, convs_without_predators)

if __name__ == "__main__":
    process_training_corpus()
