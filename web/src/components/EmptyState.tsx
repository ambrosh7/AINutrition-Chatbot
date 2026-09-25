export type ExamplePrompt = {
  id: string;
  tag: string;
  tagClass?: "safety" | "thermal" | "kinetics";
  icon: string;
  ref: string;
  body: string;
  foot: string;
  message: string;
};

export const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    id: "bioavailability",
    tag: "BIOAVAILABILITY",
    icon: "nutrition",
    ref: "REF:PUBMED",
    body: "Non-heme iron absorption factors in leafy legumes: Phytate dephosphorylation thresholds",
    foot: "Ascorbic acid synergistic ratio",
    message:
      "What factors affect non-heme iron absorption from leafy legumes, and how does phytate influence it?",
  },
  {
    id: "safety",
    tag: "FOOD SAFETY PROTOCOL",
    tagClass: "safety",
    icon: "shield_with_heart",
    ref: "FDA 2022",
    body: "Safe cooling curves & spore germination risks for cooked rice: Bacillus cereus",
    foot: "60°C → 21°C in 120min envelope",
    message:
      "What is the safe cooling guidance for cooked rice to reduce Bacillus cereus spore germination risk?",
  },
  {
    id: "thermal",
    tag: "THERMAL CHEMISTRY",
    tagClass: "thermal",
    icon: "local_fire_department",
    ref: "EFSA-CONTAM",
    body: "Maillard reaction temperature thresholds and acrylamide formation in starchy tubers",
    foot: "Free asparagine & reducing sugars",
    message:
      "At what temperatures does the Maillard reaction become significant, and how does acrylamide form in starchy foods?",
  },
  {
    id: "kinetics",
    tag: "METABOLIC KINETICS",
    tagClass: "kinetics",
    icon: "timeline",
    ref: "DIABETES CARE",
    body: "Soluble β-glucan viscosity and postprandial glycemic curve flattening mechanisms",
    foot: "Gastric emptying rate delay",
    message:
      "How does soluble beta-glucan viscosity affect postprandial glycemic response?",
  },
];

export const SUGGESTION_CHIPS = [
  "Lentil cooking kinetics",
  "Salmonella thermal death time",
  "Raw milk listeria risk",
];

type Props = {
  disabled: boolean;
  onPick: (message: string) => void;
};

export function EmptyState({ disabled, onPick }: Props) {
  return (
    <div className="empty-state">
      <div className="empty-emblem">
        <div className="empty-emblem-box" aria-hidden>
          <span className="material-symbols-outlined">science</span>
        </div>
        <span className="empty-emblem-tag" aria-hidden>
          ΔG°
        </span>
      </div>
      <span className="empty-eyebrow">Analytical Bio-Chemistry Interface</span>
      <h1 className="empty-title">
        Clinical Food Science & Nutrition Intelligence
      </h1>
      <p className="empty-copy">
        Ask precise questions regarding micronutrient bioavailability, foodborne
        pathogen safety, chemical preservation, and thermal culinary kinetics.
      </p>
      <div className="prompt-grid">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt.id}
            type="button"
            className="prompt-card"
            disabled={disabled}
            onClick={() => onPick(prompt.message)}
          >
            <div className="prompt-card-top">
              <span
                className={`prompt-card-tag${prompt.tagClass ? ` ${prompt.tagClass}` : ""}`}
              >
                <span className="material-symbols-outlined">{prompt.icon}</span>
                {prompt.tag}
              </span>
              <span className="prompt-card-ref">{prompt.ref}</span>
            </div>
            <p className="prompt-card-body">{prompt.body}</p>
            <div className="prompt-card-foot">
              <span>{prompt.foot}</span>
              <span className="material-symbols-outlined">arrow_forward</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
