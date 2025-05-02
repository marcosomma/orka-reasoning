import { Agent } from "../../types";

export function JoinInputsEditor({ agent, group }: { agent: Agent, group: string }) {
  return (
    <div className="p-2 border rounded">
      <h3 className="font-bold mb-2" style={{ marginTop: 30 }}>Join Data</h3>
      <p>Joining signals forked by:</p>
      <input
            key={group}
            type="text"
            value={group}
            disabled
            className="border p-1 rounded w-40 bg-gray-900 text-gray-100"
            style={{ width: "80%", marginTop: 10 }}
          />
    </div>
  );
}
