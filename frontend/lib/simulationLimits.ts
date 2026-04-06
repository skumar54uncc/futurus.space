/** Must stay in sync with backend `core.config.Settings.simulation_limits`. */
export const OPEN_ACCESS_AGENT_CAP = 1000;
export const OPEN_ACCESS_TURN_CAP = 40;

/** Fast defaults used for one-click launch; caps remain available for advanced flows. */
export const DEFAULT_LAUNCH_AGENT_COUNT = 80;
export const DEFAULT_LAUNCH_TURN_COUNT = 12;

export type LaunchPreset = {
	id: "fast" | "balanced" | "deep" | "max";
	label: string;
	agent_count: number;
	max_turns: number;
	note: string;
};

export const LAUNCH_PRESETS: LaunchPreset[] = [
	{ id: "fast", label: "Fast", agent_count: 80, max_turns: 12, note: "Quick validation" },
	{ id: "balanced", label: "Balanced", agent_count: 200, max_turns: 20, note: "Good signal/cost" },
	{ id: "deep", label: "Deep", agent_count: 500, max_turns: 30, note: "Richer scenario coverage" },
	{ id: "max", label: "Max Scale", agent_count: 1000, max_turns: 40, note: "Full production run" },
];

/** Reference scale for marketing / upgrade messaging (not current caps). */
export const FULL_SCALE_AGENT_CAP = 1000;
export const FULL_SCALE_TURN_CAP = 40;
