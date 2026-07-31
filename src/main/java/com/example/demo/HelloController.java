package com.example.demo;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.net.InetAddress;
import java.net.UnknownHostException;

@Controller
public class HelloController {

    @GetMapping("/")
    public String index(Model model) {
        String podIp = "127.0.0.1";
        try {
            podIp = InetAddress.getLocalHost().getHostAddress();
        } catch (UnknownHostException ignored) {}

        model.addAttribute("podIp", podIp);
        model.addAttribute("javaVersion", System.getProperty("java.version"));
        model.addAttribute("environment", System.getenv().getOrDefault("KUBERNETES_PORT", "Local Workstation").equals("Local Workstation") ? "Local" : "EKS Production Pod");

        return "index";
    }
}