import os
import json
import re

with open('synthetic_full.json', 'r') as json_file:
    results = json.load(json_file)
import tkinter as tk
from tkinter import scrolledtext, ttk
import tkinter as tk
from tkinter import scrolledtext, ttk

class ConversationViewer:
    def __init__(self, root, conversations):
        self.root = root
        self.conversations = conversations
        self.filtered_conversations = conversations

        self.channel_var = tk.StringVar(value="All")
        self.scam_var = tk.BooleanVar()
        self.persona_var = tk.StringVar(value="Persona 1")

        self.setup_ui()

    def setup_ui(self):
        # Dropdown menu for channels
        channel_frame = tk.Frame(self.root)
        channel_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        tk.Label(channel_frame, text="Select Channel:", font=("Arial", 12, "bold")).pack(anchor='w')
        self.channel_dropdown = ttk.Combobox(channel_frame, textvariable=self.channel_var)
        self.channel_dropdown['values'] = ["All"] + list({conv['channel_topic']['channel'] for conv in self.conversations})
        self.channel_dropdown.pack(anchor='w')
        self.channel_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_conversation_list())

        # Checkbox for filtering scams
        scam_frame = tk.Frame(self.root)
        scam_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')
        self.scam_checkbox = tk.Checkbutton(scam_frame, text="Show Only Scams", variable=self.scam_var, command=self.update_conversation_list)
        self.scam_checkbox.pack(anchor='w')

        # Listbox for selecting conversations
        conversation_frame = tk.Frame(self.root)
        conversation_frame.grid(row=2, column=0, padx=10, pady=10, sticky='nsew')
        self.conversation_list = tk.Listbox(conversation_frame)
        self.conversation_list.pack(fill='both', expand=True)
        self.conversation_list.bind('<<ListboxSelect>>', self.on_select)

        # Grid layout for persona, externalities, and chat history
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=3)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_rowconfigure(4, weight=1)

        # Persona Selector
        persona_selector_frame = tk.Frame(self.root)
        persona_selector_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        tk.Label(persona_selector_frame, text="Select Persona:", font=("Arial", 12, "bold")).pack(anchor='w')
        tk.Radiobutton(persona_selector_frame, text="Persona 1", variable=self.persona_var, value="Persona 1", command=self.update_persona_display).pack(anchor='w')
        tk.Radiobutton(persona_selector_frame, text="Persona 2", variable=self.persona_var, value="Persona 2", command=self.update_persona_display).pack(anchor='w')

        # Persona Bio
        persona_bio_frame = tk.Frame(self.root)
        persona_bio_frame.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')
        tk.Label(persona_bio_frame, text="Persona Bio", font=("Arial", 12, "bold")).pack(anchor='w')
        self.persona_bio_text = scrolledtext.ScrolledText(persona_bio_frame, wrap=tk.WORD, width=30, height=10, font=("Arial", 10))
        self.persona_bio_text.pack(fill='both', expand=True)
        self.persona_bio_text.config(state=tk.DISABLED)

        # Persona IP/Device Info
        persona_ip_frame = tk.Frame(self.root)
        persona_ip_frame.grid(row=2, column=1, padx=10, pady=10, sticky='nsew')
        tk.Label(persona_ip_frame, text="Persona IP/Device Info", font=("Arial", 12, "bold")).pack(anchor='w')
        self.persona_ip_text = scrolledtext.ScrolledText(persona_ip_frame, wrap=tk.WORD, width=30, height=10, font=("Arial", 10))
        self.persona_ip_text.pack(fill='both', expand=True)
        self.persona_ip_text.config(state=tk.DISABLED)

        # Externalities
        externalities_frame = tk.Frame(self.root)
        externalities_frame.grid(row=3, column=1, padx=10, pady=10, sticky='nsew')
        tk.Label(externalities_frame, text="Externalities", font=("Arial", 12, "bold")).pack(anchor='w')
        self.externalities_text = scrolledtext.ScrolledText(externalities_frame, wrap=tk.WORD, width=30, height=10, font=("Arial", 10))
        self.externalities_text.pack(fill='both', expand=True)
        self.externalities_text.config(state=tk.DISABLED)

        # Channel Topic
        channel_topic_frame = tk.Frame(self.root)
        channel_topic_frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        tk.Label(channel_topic_frame, text="Channel Topic", font=("Arial", 12, "bold")).pack(anchor='w')
        self.channel_topic_text = scrolledtext.ScrolledText(channel_topic_frame, wrap=tk.WORD, width=30, height=5, font=("Arial", 10))
        self.channel_topic_text.pack(fill='both', expand=True)
        self.channel_topic_text.config(state=tk.DISABLED)

        # Chat history
        chat_frame = tk.Frame(self.root)
        chat_frame.grid(row=1, column=2, rowspan=3, padx=10, pady=10, sticky='nsew')
        chat_label = tk.Label(chat_frame, text="Chat History", font=("Arial", 12, "bold"))
        chat_label.pack(anchor='w')

        self.text_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, width=80, height=30, font=("Arial", 10))
        self.text_area.pack(fill='both', expand=True)
        self.text_area.tag_config('persona1', foreground='blue')
        self.text_area.tag_config('persona2', foreground='green')
        self.text_area.tag_config('scammer', foreground='red', font=("Arial", 10, "bold"))
        self.text_area.config(state=tk.DISABLED)

        # Display the initial list of conversations
        self.update_conversation_list()

    def update_conversation_list(self):
        selected_channel = self.channel_var.get()
        is_scam_only = self.scam_var.get()

        self.filtered_conversations = [conv for conv in self.conversations if
                                       (conv['channel_topic']['channel'] == selected_channel or selected_channel == "All") and
                                       (conv['is_scam'] or not is_scam_only)]

        self.conversation_list.delete(0, tk.END)
        for idx, conv in enumerate(self.filtered_conversations):
            self.conversation_list.insert(tk.END, f"Conversation {idx + 1}")

    def on_select(self, event):
        w = event.widget
        if w.curselection():
            index = int(w.curselection()[0])
            self.display_conversation(self.filtered_conversations[index])

    def display_conversation(self, conversation):
        self.current_conversation = conversation
        self.update_persona_display()

        # Clear the text areas
        for widget in [self.externalities_text, self.channel_topic_text, self.text_area]:
            widget.config(state=tk.NORMAL)
            widget.delete('1.0', tk.END)

        # Externalities
        self.externalities_text.insert(tk.INSERT, conversation['externalities'])
        self.externalities_text.config(state=tk.DISABLED)

        # Channel Topic
        self.channel_topic_text.insert(tk.INSERT, f"Channel: {conversation['channel_topic']['channel']}\nTopic: {conversation['channel_topic']['topic']}")
        self.channel_topic_text.config(state=tk.DISABLED)

        # Chat history
        for chat in conversation['chat_history']:
            name = chat['name']
            timestamp = chat['timestamp']
            message = chat['chat']
            if name == conversation['persona1_bio']['name']:
                self.text_area.insert(tk.INSERT, f"{name} [{timestamp}]: {message}\n", "persona1")
            elif name == conversation['persona2_bio']['name'] and conversation['is_scam']:
                self.text_area.insert(tk.INSERT, f"{name} (Scammer) [{timestamp}]: {message}\n", "scammer")
            else:
                self.text_area.insert(tk.INSERT, f"{name} [{timestamp}]: {message}\n", "persona2")
        self.text_area.config(state=tk.DISABLED)

    def update_persona_display(self):
        if self.persona_var.get() == "Persona 1":
            persona_bio = self.current_conversation['persona1_bio']['biography']
            ip_info = self.current_conversation['persona1_bio']['ip_info']
        else:
            persona_bio = self.current_conversation['persona2_bio']['biography']
            ip_info = self.current_conversation['persona2_bio']['ip_info']

        # Update Persona Bio
        self.persona_bio_text.config(state=tk.NORMAL)
        self.persona_bio_text.delete('1.0', tk.END)
        self.persona_bio_text.insert(tk.INSERT, persona_bio)
        self.persona_bio_text.config(state=tk.DISABLED)

        # Update Persona IP/Device Info
        ip_info_text = f"Fraud Score: {ip_info['fraud_score']}\nCountry Code: {ip_info['country_code']}\nRegion: {ip_info['region']}\nCity: {ip_info['city']}\nISP: {ip_info['ISP']}\nASN: {ip_info['ASN']}\nOrganization: {ip_info['organization']}\nIs Crawler: {ip_info['is_crawler']}\nTimezone: {ip_info['timezone']}\nMobile: {ip_info['mobile']}\nHost: {ip_info['host']}\nProxy: {ip_info['proxy']}\nVPN: {ip_info['vpn']}\nTOR: {ip_info['tor']}\nActive VPN: {ip_info['active_vpn']}\nActive TOR: {ip_info['active_tor']}\nRecent Abuse: {ip_info['recent_abuse']}\nBot Status: {ip_info['bot_status']}\nZip Code: {ip_info['zip_code']}\nLatitude: {ip_info['latitude']}\nLongitude: {ip_info['longitude']}\nIP: {ip_info['IP']}"
        self.persona_ip_text.config(state=tk.NORMAL)
        self.persona_ip_text.delete('1.0', tk.END)
        self.persona_ip_text.insert(tk.INSERT, ip_info_text)
        self.persona_ip_text.config(state=tk.DISABLED)

root = tk.Tk()
root.title("Conversation Viewer")
app = ConversationViewer(root, results)
root.mainloop()