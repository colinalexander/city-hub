"use client";

import React, { useState } from "react";
import axios, { AxiosResponse } from "axios";
import styles from "./page.module.css";
import Groq from "groq-sdk";
import ReactMarkdown from "react-markdown";

interface ChatbotResponse {
  response: string;
}

const groq = new Groq({
  apiKey: "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",
  dangerouslyAllowBrowser: true,
});
const Chatbot: React.FC = () => {
  const [message, setMessage] = useState<string>("");
  const [messages, setMessages] = useState<Array<string>>([]);
  const [response, setResponse] = useState<Array<string>>([]);

  async function getGroqChatCompletion() {
    return groq.chat.completions.create({
      messages: [
        {
          role: "user",
          content: message,
        },
      ],
      model: "llama3-8b-8192",
    });
  }

  async function handleSubmit() {
    const chatCompletion = await getGroqChatCompletion();
    // Print the completion returned by the LLM.

    setMessages((oldmessages) => {
      const newMessage = [...oldmessages, message];
      return newMessage;
    });

    setResponse((oldresponse) => {
      const newResponse = [
        ...oldresponse,
        chatCompletion.choices[0]?.message?.content || "",
      ];
      return newResponse;
    });
  }

  // const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
  //   e.preventDefault();
  //   try {
  //     const res: AxiosResponse<ChatbotResponse> = await axios.post(
  //       "/api/chatbot",
  //       { message }
  //     );
  //     setResponse(res.data.response);
  //   } catch (err) {
  //     console.error(err);
  //   }
  //   setMessage("");
  // };

  return (
    <div className={styles.chatbotcontainer}>
      <div className={styles.chatheader}>
        <h2>Welcome to CityHub</h2>
      </div>
      <div className={styles.chatheader}>
        <h4>Chat with me!</h4>
      </div>
      <div className={styles.chatbody}>
        <div className={styles.chatmessages}>
          {/* Render chat messages here */}

          {/* <div className={styles.user-message}>
            <span>{message}</span>
          </div> */}
          <div className={styles.botmessage}>
            {response?.map((r, i) => (
              <>
                <div className={styles.chathistorymessage}>
                  <h4 className={styles.chathistorymessage}>{messages[i]}</h4>
                  <ReactMarkdown>{r}</ReactMarkdown>
                </div>
              </>
            ))}
          </div>
        </div>
      </div>
      <div className={styles.chatinput}>
        <textarea
          rows={5}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
          className={styles.inputfield}
        />
        <button className={styles.sendbutton} onClick={handleSubmit}>
          Send
        </button>
      </div>
    </div>
  );
};

export default Chatbot;
