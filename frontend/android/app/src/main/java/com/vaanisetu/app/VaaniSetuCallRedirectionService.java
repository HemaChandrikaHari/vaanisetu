package com.vaanisetu.app;

import android.content.SharedPreferences;
import android.net.Uri;
import android.telecom.CallRedirectionService;
import android.telecom.PhoneAccountHandle;
import android.util.Log;

/**
 * Diagnostic-safe outgoing-call hook.
 * It records invocation without storing the dialled number or changing call routing.
 */
public final class VaaniSetuCallRedirectionService extends CallRedirectionService {
    private static final String TAG = "VaaniSetuRedirect";
    private static final String PREFS = "vaanisetu_call_prefs";
    private static final String KEY_LAST_INVOCATION = "last_redirection_invocation";
    private static final String KEY_LAST_DECISION = "last_redirection_decision";

    @Override
    public void onPlaceCall(
            Uri handle,
            PhoneAccountHandle initialPhoneAccount,
            boolean allowInteractiveResponse) {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String decision = handle == null
                ? "invoked_invalid_handle"
                : "invoked_pass_through_gateway_pending";

        // Do not persist the number, contact, or PhoneAccount details.
        prefs.edit()
                .putLong(KEY_LAST_INVOCATION, System.currentTimeMillis())
                .putString(KEY_LAST_DECISION, decision)
                .apply();

        Log.i(TAG, "Call-redirection service invoked; passing call through unchanged.");
        placeCallUnmodified();
    }
}
