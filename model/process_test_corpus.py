"""
Download the pan12 dataset before using
"""
import os
from bs4 import BeautifulSoup

def read_xml_file(file_path):
    """Read the XML file containing the training corpus."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def fetch_pervert_authors_list(file_path):
    """Read the list of perverted authors from a text file."""
    predators = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            predators.append(line.strip())
    return predators

def fetch_true_pervert_convs(file_path):
    """Read the list of confirmed convs with perverted content"""
    true_pervert_convs = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            true_pervert_convs.append(line.strip().split('\t')[0])
    return list(set(true_pervert_convs))

def separate_conversations_by_pervertedness(soup, perverted_authors, true_perverted_convs):
    """
    Separate conversations by whether they contain a perverted author or were flagged 
    for perverted content.
    """
    perverted_convs = []
    not_perverted_convs = []

    for conversation in soup.find_all('conversation'):
        contains_perverted = False
        for message in conversation.find_all('message'):
            author = message.find('author').text.strip()
            if author in perverted_authors:
                contains_perverted = True
                break
        if conversation in true_perverted_convs:
            contains_perverted = True

        if contains_perverted:
            perverted_convs.append(conversation)
        else:
            not_perverted_convs.append(conversation)

    return perverted_convs, not_perverted_convs

def write_conversations_to_files(perverted_convs, not_perverted_convs):
    """Write each conversation to a separate text file."""
    os.makedirs('perverted', exist_ok=True)
    os.makedirs('not_perverted', exist_ok=True)

    # Write conversations with predators
    for conv in perverted_convs:
        conv_id = conv['id']
        filename = os.path.join('perverted', f'{conv_id}.txt')
        with open(filename, 'w', encoding='utf-8') as file:
            for message in conv.find_all('message'):
                author = message.find('author').text.strip()
                text = message.find('text').text.strip()
                file.write(f'Author: {author}\nText: {text}\n\n')
        print(f'Perverted conversation {conv_id} written to {filename}')

    # Write conversations without predators
    for conv in not_perverted_convs:
        conv_id = conv['id']
        filename = os.path.join('not_perverted', f'{conv_id}.txt')
        messages = conv.find_all('message')
        if len(messages) > 20:
            with open(filename, 'w', encoding='utf-8') as file:
                for message in messages:
                    author = message.find('author').text.strip()
                    text = message.find('text').text.strip()
                    file.write(f'Author: {author}\nText: {text}\n\n')
            print(f'Not perverted conversation {conv_id} written to {filename}')

def process_test_corpus():
    """Main function to process the training corpus."""
    test_corpus_file_path = 'pan12/pan12-sexual-predator-identification-test-corpus-2012-05-21/pan12-sexual-predator-identification-test-corpus-2012-05-17.xml'
    perverts_txt_file_path = 'pan12/pan12-sexual-predator-identification-test-corpus-2012-05-21/pan12-sexual-predator-identification-groundtruth-problem1.txt'
    perverted_convs_file_path = 'pan12/pan12-sexual-predator-identification-test-corpus-2012-05-21/pan12-sexual-predator-identification-groundtruth-problem2.txt'


    xml_content = read_xml_file(test_corpus_file_path)
    soup = BeautifulSoup(xml_content, 'xml')

    perverted_authors = fetch_pervert_authors_list(perverts_txt_file_path)
    true_perverted_convs = fetch_true_pervert_convs(perverted_convs_file_path)

    perverted_convs, not_perverted_convs = separate_conversations_by_pervertedness(soup, perverted_authors, true_perverted_convs)

    write_conversations_to_files(perverted_convs, not_perverted_convs)

if __name__ == "__main__":
    process_test_corpus()
