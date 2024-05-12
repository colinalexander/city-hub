import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import PromptInput from "../PromptInput/PromptInput";
import "./App.css";
import { ResponseInterface } from "../PromptResponseList/response-interface";
import PromptResponseList from "../PromptResponseList/PromptResponseList";
import LoadingIndicator from "./LoadingIndicator";
import logo from "../../img/logo.png";

const API_URL = "http://localhost:9100/askcityhub";
// const API_URL =
//   "https://8f4b-2601-645-c600-65a6-b0b0-49c1-8d55-feac.ngrok-free.app";

type ModelValueType = "gpt" | "codex" | "image";
const App = () => {
  const [responseList, setResponseList] = useState<ResponseInterface[]>([
    // {
    //   id: "1adaw",
    //   response: "this is weafaffaew waef awefwaef",
    //   selfFlag: true,
    //   error: false,
    //   // image: "adbawed";
    // },
  ]);
  const [prompt, setPrompt] = useState<string>("");
  const [promptToRetry, setPromptToRetry] = useState<string | null>(null);
  const [uniqueIdToRetry, setUniqueIdToRetry] = useState<string | null>(null);
  const [modelValue, setModelValue] = useState<ModelValueType>("gpt");
  const [isLoading, setIsLoading] = useState(false);
  const [dots, setDots] = useState(0);
  const [loadingText, setLoadingText] = useState("");
  let loadInterval: number | undefined;

  const generateUniqueId = () => {
    const timestamp = Date.now();
    const randomNumber = Math.random();
    const hexadecimalString = randomNumber.toString(16);

    return `id-${timestamp}-${hexadecimalString}`;
  };

  const htmlToText = (html: string) => {
    const temp = document.createElement("div");
    temp.innerHTML = html;
    return temp.textContent;
  };

  const delay = (ms: number) => {
    return new Promise((resolve) => setTimeout(resolve, ms));
  };

  const addResponse = (selfFlag: boolean, response?: string) => {
    const uid = generateUniqueId();
    setResponseList((prevResponses) => [
      ...prevResponses,
      {
        id: uid,
        response,
        selfFlag,
      },
    ]);
    return uid;
  };

  const getDotsString = useCallback(() => {
    let str = "";
    for (let i = 0; i < dots; i++) {
      str += ".";
    }
    return str;
  }, [dots]);

  const updateResponse = useCallback(
    (uid: string, updatedObject: Record<string, unknown>) => {
      setResponseList((prevResponses) => {
        const updatedList = [...prevResponses];
        const index = prevResponses.findIndex(
          (response) => response.id === uid
        );
        if (index > -1) {
          updatedList[index] = {
            ...updatedList[index],
            ...updatedObject,
          };
        }
        return updatedList;
      });
    },
    []
  );

  const regenerateResponse = async () => {
    await getGPTResult(promptToRetry, uniqueIdToRetry);
  };

  useEffect(() => {
    let s = "";
    for (let d = 0; d < dots; d++) {
      s += ".";
    }
    setLoadingText(s);
  }, [dots, setLoadingText]);

  // Testing code
  const _getGPTResult = useCallback(
    async (
      _promptToRetry?: string | null,
      _uniqueIdToRetry?: string | null
    ) => {
      // Get the prompt input
      const _prompt = _promptToRetry ?? htmlToText(prompt);

      // If a response is already being generated or the prompt is empty, return
      if (isLoading || !_prompt) {
        return;
      }

      setIsLoading(true);

      // Clear the prompt input
      setPrompt("");

      let uniqueId: string;
      if (_uniqueIdToRetry) {
        uniqueId = _uniqueIdToRetry;
      } else {
        // Add the self prompt to the response list
        addResponse(true, _prompt);
        uniqueId = addResponse(false);
        // await delay(50);
        // addLoader(uniqueId);
      }

      // const interval = setInterval(() => {
      //   console.log("dwadw ", dots);
      //   setDots((d) => d + 1);
      //   updateResponse(uniqueId, {
      //     response: loadingText,
      //   });
      // }, 500);

      try {
        // Send a POST request to the API with the prompt in the request body
        const response = await axios.post("https://dummyjson.com/posts/add", {
          title: "abc this is the sample test",
          userId: 2,
        });

        await delay(5000);
        // clearInterval(interval);

        console.log(response?.data);

        updateResponse(uniqueId, {
          response: response?.data?.title?.trim(),
        });

        setPromptToRetry(null);
        setUniqueIdToRetry(null);
      } catch (err) {
        setPromptToRetry(_prompt);
        setUniqueIdToRetry(uniqueId);
        updateResponse(uniqueId, {
          // @ts-ignore
          response: `Error: ${err.message}`,
          error: true,
        });
      } finally {
        // Clear the loader interval
        clearInterval(loadInterval);
        setIsLoading(false);
      }
    },
    [
      prompt,
      isLoading,
      addResponse,
      dots,
      updateResponse,
      loadingText,
      loadInterval,
    ]
  );

  const getGPTResult = async (
    _promptToRetry?: string | null,
    _uniqueIdToRetry?: string | null
  ) => {
    // Get the prompt input
    const _prompt = _promptToRetry ?? htmlToText(prompt);

    // If a response is already being generated or the prompt is empty, return
    if (isLoading || !_prompt) {
      return;
    }

    setIsLoading(true);

    // Clear the prompt input
    setPrompt("");

    let uniqueId: string;
    if (_uniqueIdToRetry) {
      uniqueId = _uniqueIdToRetry;
    } else {
      // Add the self prompt to the response list
      addResponse(true, _prompt);
      uniqueId = addResponse(false);
      await delay(50);
      // addLoader(uniqueId);
    }

    try {
      // Send a POST request to the API with the prompt in the request body
      console.log(_prompt);
      const response = await axios.post(API_URL, {
        question: _prompt,
      });
      updateResponse(uniqueId, {
        response: response?.data?.trim(),
      });

      setPromptToRetry(null);
      setUniqueIdToRetry(null);
    } catch (err) {
      setPromptToRetry(_prompt);
      setUniqueIdToRetry(uniqueId);
      updateResponse(uniqueId, {
        // @ts-ignore
        response: `Error: ${err.message}`,
        error: true,
      });
    } finally {
      // Clear the loader interval
      clearInterval(loadInterval);
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          alignItems: "center",
          padding: 20,
        }}
      >
        <img
          src={logo}
          style={{ height: 100, width: 100, marginRight: 30 }}
          className="App-logo"
          alt="logo"
        />
        <h1 style={{}}>Welcome to CityHub</h1>
      </div>
      <div id="response-list">
        <PromptResponseList responseList={responseList} key="response-list" />
        {isLoading && <LoadingIndicator />}
      </div>

      {/* {uniqueIdToRetry && (
        <div id="regenerate-button-container">
          <button
            id="regenerate-response-button"
            className={isLoading ? "loading" : ""}
            onClick={() => regenerateResponse()}
          >
            Regenerate Response
          </button>
        </div>
      )} */}
      <div id="input-container">
        <PromptInput
          prompt={prompt}
          onSubmit={() => getGPTResult()}
          key="prompt-input"
          updatePrompt={(prompt) => setPrompt(prompt)}
        />
        <button
          id="submit-button"
          className={isLoading ? "loading" : ""}
          onClick={() => getGPTResult()}
        ></button>
      </div>
    </div>
  );
};

export default App;
