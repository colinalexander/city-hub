// Add this import statement at the top of the file
import axios from "axios";

// ...

const handleSendMessage = async () => {
  if (input.trim() === "") return;

  // Add the user message to the messages array
  setMessages([...messages, { role: "user", text: input }]);

  try {
    // Send the user message to the ChatGPT API
    const response = await axios.post(
      "https://api.openai.com/v1/engines/davinci-codex/completions",
      {
        prompt: `User: ${input}\nChatGPT:`,
        max_tokens: 150,
      },
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer YOUR_API_KEY",
        },
      }
    );

    // Extract the bot response from the API response
    const botResponse = response.data.choices[0].text;

    // Add the bot response to the messages array
    setMessages([...messages, { role: "bot", text: botResponse }]);

    // Clear the input field
    setInput("");
  } catch (error) {
    console.error("Error sending message:", error);
  }
};
