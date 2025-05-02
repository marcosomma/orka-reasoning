import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../redux/store";
import { clearNotification } from "../redux/notificationSlice";

const Notification: React.FC = () => {
  const message = useSelector((state: RootState) => state.notification.message);
  const dispatch = useDispatch();

  useEffect(() => {
    if (message) {
      const timeout = setTimeout(() => {
        dispatch(clearNotification());
      }, 2500);
      return () => clearTimeout(timeout);
    }
  }, [message, dispatch]);

  if (!message) return null;

  return (
    <div style={{
      position: "fixed",
      top: "20px",
      right: "20px",
      backgroundColor: "#333",
      color: "#fff",
      padding: "10px 20px",
      borderRadius: "6px",
      boxShadow: "0 2px 10px rgba(0,0,0,0.5)",
      zIndex: 9999,
      fontSize: "0.9rem",
    }}>
      {message}
    </div>
  );
};

export default Notification;
