import React from "react";
import { useState, useEffect } from "react";
import MetaImg from "../../img/meta.png";

// const LoadingIndicator = () => {
//   return (
//     <div className="loading-indicator">
//       <div className="loading-spinner">
//         {/* <div className="loading-spinner-inner"> */}
//         <img style={{ height: 40, width: 40 }} src={MetaImg} alt="avatar" />
//         {/* </div> */}
//       </div>
//     </div>
//   );
// };

const LoadingIndicator = () => {
  const [dots, setDots] = useState(1);
  const [id, setId] = useState(null);

  useEffect(() => {
    const i = setInterval(() => {
      setDots((d) => (d < 3 ? d + 1 : 1));
    }, 1000);
    setId(i);

    return () => {
      if (id) clearInterval(id);
    };
  }, [dots, id]);

  return (
    <div className="loading-indicator">
      {Array(dots)
        .fill()
        .map((_, index) => (
          <span key={index} className="dot">
            •
          </span>
        ))}
    </div>
  );
};

export default LoadingIndicator;

// const LoadingIndicator = () => {
//   const [str, setStr] =

//     loadInterval = setInterval(() => {
//       // Update the text content of the loading indicator
//       element.textContent += ".";

//       // If the loading indicator has reached three dots, reset it
//       if (element.textContent === "....") {
//         element.textContent = "";
//       }
//     }, 300);
//   };

//   return (
//     <div className="loading-indicator">
//       <div className="loading-spinner">...</div>
//     </div>
//   );
// };

// export default LoadingIndicator;
