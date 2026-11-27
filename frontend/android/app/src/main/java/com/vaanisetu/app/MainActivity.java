package com.vaanisetu.app;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(android.os.Bundle savedInstanceState) {
        registerPlugin(CallRedirectionPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
