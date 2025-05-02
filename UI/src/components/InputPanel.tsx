interface Props {
  input: string;
  setInput: (val: string) => void;
}

const InputPanel: React.FC<Props> = ({ input, setInput }) => (
  <div className="input-panel">
    <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Enter input..." />
  </div>
);

export default InputPanel;
