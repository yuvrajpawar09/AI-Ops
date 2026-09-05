package com.aiops.inventoryservice.controller;

import com.aiops.inventoryservice.dto.InventoryRequest;
import com.aiops.inventoryservice.dto.InventoryResponse;
import com.aiops.inventoryservice.service.InventoryService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/inventory")
public class InventoryController {

    private final InventoryService inventoryService;

    public InventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @PostMapping("/reserve")
    public ResponseEntity<InventoryResponse> reserve(@RequestBody InventoryRequest request) {
        InventoryResponse response = inventoryService.reserve(request);
        return ResponseEntity.ok(response);
    }
}
