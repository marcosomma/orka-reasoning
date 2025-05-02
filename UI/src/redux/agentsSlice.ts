import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Agent } from '../types';

const initialState: Agent[] = [];

const agentsSlice = createSlice({
  name: 'agents',
  initialState,
  reducers: {
    addAgent: (state, action: PayloadAction<Agent>) => {
      state.push(action.payload);
    },
    updateAgent: (state, action: PayloadAction<Agent>) => {
      const index = state.findIndex(agent => agent.id === action.payload.id);
      if (index !== -1) state[index] = action.payload;
    },
    deleteAgent: (state, action: PayloadAction<string>) => {
      return state.filter(agent => agent.id !== action.payload);
    }
  }
});

export const { addAgent, updateAgent, deleteAgent } = agentsSlice.actions;
export default agentsSlice.reducer;
