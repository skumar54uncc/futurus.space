/**
 * Require a confirmed failed status before opening the failed dialog.
 * Avoids flash when a transient poll / mid-redeploy briefly sees status=failed.
 */

/** Wait this long, then re-check before opening. */
export const FAILED_DIALOG_CONFIRM_MS = 2500;

export function shouldScheduleFailedConfirm(status: string | undefined | null): boolean {
  return status === "failed";
}

export function shouldOpenFailedDialogAfterConfirm(
  statusAfterWait: string | undefined | null
): boolean {
  return statusAfterWait === "failed";
}
