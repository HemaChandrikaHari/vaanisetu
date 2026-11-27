package com.vaanisetu.app;

import android.net.Uri;
import android.telecom.CallRedirectionService;
import android.telecom.PhoneAccountHandle;
import android.util.Log;

/**
 * Android outgoing-call interception entry point.
 *
 * Safety rule: never redirect a call until the Exotel two-leg gateway,
 * recipient metadata handoff, and media protocol have been verified.
 * Until then every outgoing call proceeds normally.
 */
public final class VaaniSetuCallRedirectionService extends CallRedirectionService {
    private static final String TAG = "VaaniSetuRedirect";
    private static final String PREFS = "vaanisetu_call_prefs";
    private static final String KEY_ROUTING_ENABLED = "routing_enabled";
    private static final String KEY_GATEWAY_READY = "gateway_ready";

    @Override
    public void onPlaceCall(
            Uri handle,
            PhoneAccountHandle initialPhoneAccount,
            boolean allowInteractiveResponse) {
        android.content.SharedPreferences prefs =
                getSharedPreferences(PREFS, MODE_PRIVATE);

        boolean routingEnabled = prefs.getBoolean(KEY_ROUTING_ENABLED, false);
        boolean gatewayReady = prefs.getBoolean(KEY_GATEWAY_READY, false);

        // Do not interfere with emergency calls, malformed numbers, or normal
        // calls while the provider gateway is not verified.
        if (handle == null || !routingEnabled || !gatewayReady) {
            Log.i(TAG, "Passing outgoing call through unchanged.");
            placeCallUnmodified();
            return;
        }

        // Deliberately fail closed. The gateway implementation must be added
        // only after Exotel confirms the exact inbound/outbound bridge flow.
        Log.w(TAG, "Routing requested but gateway adapter is not implemented; passing through.");
        placeCallUnmodified();
    }
}
