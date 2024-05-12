// src/Chatbot.js
import React, { useState } from "react";

const ChatbotHeading = "Ask Cityhub anything";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const handleInputChange = (e) => {
    setInput(e.target.value);
  };

  const handleSendMessage = () => {
    // Implement this function to send user messages to ChatGPT
  };

  return (
    <>
      <h3>{ChatbotHeading}</h3>
      <div style={chatbotStyles.chatbot}>
        <div style={chatbotStyles.chatbox}>
          <div style={chatbotStyles.messages}>
            {messages.map((message, index) => (
              return <Message/>
              
            ))}
          </div>
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder="Type a message..."
            style={chatbotStyles.input}
          />
          <button onClick={handleSendMessage} style={chatbotStyles.button}>
            Send
          </button>
        </div>
      </div>
    </>
  );
}

const chatbotStyles = {
  chatbot: {
    width: "300px",
    backgroundColor: "#f0f0f0",
    border: "1px solid #ccc",
    borderRadius: "5px",
    margin: "0 auto",
    padding: "10px",
  },
  chatbox: {
    display: "flex",
    flexDirection: "column",
  },
  messages: {
    maxHeight: "300px",
    overflowY: "scroll",
  },
  message: {
    marginBottom: "10px",
  },
  botMessage: {
    backgroundColor: "#007bff",
    color: "white",
    padding: "5px 10px",
    borderRadius: "5px",
    marginLeft: "auto",
  },
  userMessage: {
    backgroundColor: "#e0e0e0",
    padding: "5px 10px",
    borderRadius: "5px",
    marginRight: "auto",
  },
  input: {
    width: "100%",
    padding: "5px",
    margin: "5px",
    border: "1px solid #ccc",
    borderRadius: "5px",
    marginBottom: "10px",
  },
  button: {
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    padding: "10px 20px",
    borderRadius: "5px",
    cursor: "pointer",
  },
};
