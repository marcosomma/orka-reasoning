import { configureStore } from '@reduxjs/toolkit';
import agentsReducer from './agentsSlice';
import notificationReducer from "./notificationSlice";

const store = configureStore({
  reducer: {
    agents: agentsReducer,
    notification: notificationReducer,
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export default store;
