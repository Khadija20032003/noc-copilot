import Icon, { type IconName } from "./Icon";

interface ExampleGroup {
  label: string;
  hint: string;
  icon: IconName;
  questions: string[];
}

// Same questions as the README "Example questions" section and eval/golden.jsonl.
// Route ids must match data/scenarios.json: R1 healthy, R2 RC2, R3 RC6, R4 RC8, R5 RC7, R6 RC5.
const GROUPS: ExampleGroup[] = [
  {
    label: "Knowledge base",
    hint: "Runbooks",
    icon: "book",
    questions: [
      "What is PCI mod 30 and why does it matter in 5G NR?",
      "Which severity applies when one cell has been below 600 Mbps for 45 minutes?",
    ],
  },
  {
    label: "Network data",
    hint: "SQL tools",
    icon: "database",
    questions: [
      "What is the average number of scheduled RBs on route R4?",
      "Do PCI 205 and PCI 145 have a PCI mod 30 conflict?",
    ],
  },
  {
    label: "Diagnosis",
    hint: "All agents",
    icon: "route",
    questions: [
      "Why is the throughput low on route R2?",
      "Diagnose route R3 and propose a ticket if needed.",
      "Route R4 has low throughput but the radio looks fine. What is the root cause?",
      "Why does throughput dip repeatedly on route R6? Propose a ticket if needed.",
    ],
  },
];

interface Props {
  disabled: boolean;
  onPick: (question: string) => void;
}

export default function ExampleQuestions({ disabled, onPick }: Props) {
  return (
    <nav className="examples" aria-label="Example questions">
      <h2 className="section-label">Example questions</h2>
      {GROUPS.map((group) => (
        <section key={group.label} className="example-group">
          <div className="example-group-head">
            <Icon name={group.icon} size={15} />
            <span className="example-label">{group.label}</span>
            <span className="example-hint">{group.hint}</span>
          </div>
          {group.questions.map((q) => (
            <button key={q} className="example-btn" disabled={disabled} onClick={() => onPick(q)}>
              <span>{q}</span>
              <Icon name="chevron" size={14} />
            </button>
          ))}
        </section>
      ))}
    </nav>
  );
}
