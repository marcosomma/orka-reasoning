import { Agent } from "../../types";

export function ForkInputsEditor({ agent, targetIds=[] }: { agent: Agent, targetIds: string[] }) {
  return (
    <div className="p-2 border rounded">
      <h3 className="font-bold mb-2" style={{ marginTop: 30 }}>Fork Data</h3>
      <p>The signal will be forwarded to the following agents</p>
      {targetIds.length === 0 ? (
        <p className="text-gray-500 italic">No linked fallback agents yet.</p>
      ) : (
        targetIds.map((target:string) => (
          <input
            key={target}
            type="text"
            value={target}
            disabled
            className="border p-1 rounded w-40 bg-gray-900 text-gray-100"
            style={{ width: "80%", marginTop: 10 }}
          />
        ))
      )}
    </div>
  );
}
