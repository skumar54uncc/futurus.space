/**
 * Run: npx --yes tsx lib/failedDialogHysteresis.selftest.ts
 */
import {
  shouldOpenFailedDialogAfterConfirm,
  shouldScheduleFailedConfirm,
} from "./failedDialogHysteresis";

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg);
}

assert(shouldScheduleFailedConfirm("failed"), "schedule on failed");
assert(!shouldScheduleFailedConfirm("running"), "no schedule on running");
assert(shouldOpenFailedDialogAfterConfirm("failed"), "still failed → open");
assert(!shouldOpenFailedDialogAfterConfirm("running"), "recovered → no dialog");
assert(!shouldOpenFailedDialogAfterConfirm("completed"), "completed → no dialog");

console.log("failedDialogHysteresis.selftest: ok");
