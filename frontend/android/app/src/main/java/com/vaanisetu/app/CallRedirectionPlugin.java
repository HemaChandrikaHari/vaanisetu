package com.vaanisetu.app;

import androidx.activity.result.ActivityResult;
import android.app.role.RoleManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "CallRedirection")
public class CallRedirectionPlugin extends Plugin {
    private static final String PREFS = "vaanisetu_call_prefs";
    private static final String KEY_ROUTING_ENABLED = "routing_enabled";
    private static final String KEY_GATEWAY_READY = "gateway_ready";
    private static final String KEY_SOURCE_LANGUAGE = "source_language";
    private static final String KEY_TARGET_LANGUAGE = "target_language";
    private static final String KEY_LAST_INVOCATION = "last_redirection_invocation";
    private static final String KEY_LAST_DECISION = "last_redirection_decision";

    @PluginMethod
    public void getStatus(PluginCall call) {
        JSObject result = new JSObject();
        boolean supported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q;
        boolean roleAvailable = false;
        boolean roleHeld = false;

        if (supported) {
            RoleManager roleManager =
                    (RoleManager) getContext().getSystemService(Context.ROLE_SERVICE);
            roleAvailable = roleManager != null
                    && roleManager.isRoleAvailable(RoleManager.ROLE_CALL_REDIRECTION);
            roleHeld = roleAvailable
                    && roleManager.isRoleHeld(RoleManager.ROLE_CALL_REDIRECTION);
        }

        SharedPreferences prefs = getContext()
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        result.put("supported", supported);
        result.put("roleAvailable", roleAvailable);
        result.put("roleHeld", roleHeld);
        result.put("routingEnabled", prefs.getBoolean(KEY_ROUTING_ENABLED, false));
        result.put("gatewayReady", prefs.getBoolean(KEY_GATEWAY_READY, false));
        result.put("sourceLanguage", prefs.getString(KEY_SOURCE_LANGUAGE, "te-IN"));
        result.put("targetLanguage", prefs.getString(KEY_TARGET_LANGUAGE, "hi-IN"));
        result.put("lastInvocationAt", prefs.getLong(KEY_LAST_INVOCATION, 0L));
        result.put("lastDecision", prefs.getString(KEY_LAST_DECISION, "not_observed"));
        result.put("note", "The role is granted, but call interception has not been verified on this device. Calls always pass through unchanged until the Exotel gateway is ready.");
        call.resolve(result);
    }

    @PluginMethod
    public void requestRole(PluginCall call) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            call.reject("Call redirection requires Android 10 or newer.");
            return;
        }

        RoleManager roleManager =
                (RoleManager) getContext().getSystemService(Context.ROLE_SERVICE);
        if (roleManager == null
                || !roleManager.isRoleAvailable(RoleManager.ROLE_CALL_REDIRECTION)) {
            call.reject("This Android device does not offer the call-redirection role.");
            return;
        }

        if (roleManager.isRoleHeld(RoleManager.ROLE_CALL_REDIRECTION)) {
            JSObject result = new JSObject();
            result.put("roleHeld", true);
            call.resolve(result);
            return;
        }

        Intent intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_CALL_REDIRECTION);
        startActivityForResult(call, intent, "onRoleRequestResult");
    }

    @ActivityCallback
    private void onRoleRequestResult(PluginCall call, ActivityResult result) {
        if (call == null) return;
        boolean granted = false;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            RoleManager roleManager =
                    (RoleManager) getContext().getSystemService(Context.ROLE_SERVICE);
            granted = roleManager != null
                    && roleManager.isRoleHeld(RoleManager.ROLE_CALL_REDIRECTION);
        }
        JSObject response = new JSObject();
        response.put("roleHeld", granted);
        call.resolve(response);
    }

    @PluginMethod
    public void saveLanguageDirection(PluginCall call) {
        String source = call.getString("sourceLanguage", "te-IN");
        String target = call.getString("targetLanguage", "hi-IN");
        if (source == null || target == null || source.equals(target)) {
            call.reject("Choose two different languages.");
            return;
        }
        SharedPreferences prefs = getContext()
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        prefs.edit()
                .putString(KEY_SOURCE_LANGUAGE, source)
                .putString(KEY_TARGET_LANGUAGE, target)
                .apply();
        JSObject result = new JSObject();
        result.put("saved", true);
        result.put("sourceLanguage", source);
        result.put("targetLanguage", target);
        call.resolve(result);
    }

    @PluginMethod
    public void setRoutingEnabled(PluginCall call) {
        boolean enabled = call.getBoolean("enabled", false);
        SharedPreferences prefs = getContext()
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        boolean gatewayReady = prefs.getBoolean(KEY_GATEWAY_READY, false);

        // The public API intentionally cannot enable routing until a verified
        // gateway adapter is shipped in a later release.
        if (enabled && !gatewayReady) {
            call.reject("VaaniSetu calling is not activated yet. Your normal calls remain unchanged.");
            return;
        }
        prefs.edit().putBoolean(KEY_ROUTING_ENABLED, enabled).apply();
        JSObject result = new JSObject();
        result.put("routingEnabled", enabled);
        call.resolve(result);
    }
}
