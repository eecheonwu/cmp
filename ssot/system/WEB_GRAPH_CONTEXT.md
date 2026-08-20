{
  "nodes": [
    {
      "id": "4f908858-43ae-4e1f-8f5a-bbbb1e4cdc68",
      "name": "adr-001-postgresql-primary-datastore.md",
      "type": "ADR",
      "version": 1
    },
    {
      "id": "7aec918d-406d-44b6-8606-a1849e22b2fa",
      "name": "adr-002-react-pwa-client.md",
      "type": "ADR",
      "version": 1
    },
    {
      "id": "d3ba1009-d477-4301-a0ac-99dd5111c643",
      "name": "adr-003-application-level-column-encryption.md",
      "type": "ADR",
      "version": 1
    },
    {
      "id": "69529699-03c7-47b2-85f0-b56c675adada",
      "name": "adr-004-pluggable-notification-failover.md",
      "type": "ADR",
      "version": 1
    },
    {
      "id": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "name": "c4_architecture_models.md",
      "type": "C4_DIAGRAM",
      "version": 1
    },
    {
      "id": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "name": "software_requirements_document.md",
      "type": "SRD",
      "version": 1
    },
    {
      "id": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "name": "technical_specification.md",
      "type": "TECHNICAL_SPEC",
      "version": 1
    },
    {
      "id": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "name": "test-specification.md",
      "type": "TEST_SPEC",
      "version": 1
    },
    {
      "id": "d70a271c-6f86-4b05-a29d-ebb5a91581d8",
      "name": "uml_diagrams.md",
      "type": "UML",
      "version": 1
    }
  ],
  "edges": [
    {
      "id": "573fb523-ea8e-4e59-b395-8dd390e1bea8",
      "source": "4f908858-43ae-4e1f-8f5a-bbbb1e4cdc68",
      "target": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "type": "DEPENDS_ON"
    },
    {
      "id": "f128cd8b-5028-4d50-a178-ac537329274c",
      "source": "7aec918d-406d-44b6-8606-a1849e22b2fa",
      "target": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "type": "DEPENDS_ON"
    },
    {
      "id": "6756b3b2-7a02-49ac-959b-e298d920db6a",
      "source": "d3ba1009-d477-4301-a0ac-99dd5111c643",
      "target": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "type": "DEPENDS_ON"
    },
    {
      "id": "7761d7d6-efcd-4374-b5e2-c8e357fbf817",
      "source": "69529699-03c7-47b2-85f0-b56c675adada",
      "target": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "type": "DEPENDS_ON"
    },
    {
      "id": "9b6cfe56-6797-4e70-a227-e0d0ae4e000a",
      "source": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "target": "4f908858-43ae-4e1f-8f5a-bbbb1e4cdc68",
      "type": "DEPENDS_ON"
    },
    {
      "id": "045402d8-dc8a-453f-9691-73ecf3db3ff8",
      "source": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "target": "7aec918d-406d-44b6-8606-a1849e22b2fa",
      "type": "DEPENDS_ON"
    },
    {
      "id": "21be6cfd-5c76-45b6-ba9d-17b83c6261df",
      "source": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "target": "d3ba1009-d477-4301-a0ac-99dd5111c643",
      "type": "DEPENDS_ON"
    },
    {
      "id": "08e811a2-b440-42d7-932a-bf643c4dfba9",
      "source": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "target": "69529699-03c7-47b2-85f0-b56c675adada",
      "type": "DEPENDS_ON"
    },
    {
      "id": "a8f648a2-ed13-403b-a076-65544653f9a6",
      "source": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "target": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "type": "DEPENDS_ON"
    },
    {
      "id": "16ca2791-1e85-4401-aac1-653a4f8782a1",
      "source": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "target": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "type": "DEPENDS_ON"
    },
    {
      "id": "000c17e3-f210-44a7-b977-49e8b950f7bd",
      "source": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "target": "69529699-03c7-47b2-85f0-b56c675adada",
      "type": "DEPENDS_ON"
    },
    {
      "id": "2776a956-65c8-4843-99d7-32224ff22a8c",
      "source": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "target": "d3ba1009-d477-4301-a0ac-99dd5111c643",
      "type": "DEPENDS_ON"
    },
    {
      "id": "6be780ac-424b-4fd7-8a76-faae029c9aa6",
      "source": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "target": "7aec918d-406d-44b6-8606-a1849e22b2fa",
      "type": "DEPENDS_ON"
    },
    {
      "id": "148020a7-6781-4581-80d0-ce52b106aa36",
      "source": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "target": "4f908858-43ae-4e1f-8f5a-bbbb1e4cdc68",
      "type": "DEPENDS_ON"
    },
    {
      "id": "b1e5e48e-7ec9-4a71-a662-1fc52ec40534",
      "source": "d70a271c-6f86-4b05-a29d-ebb5a91581d8",
      "target": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "type": "REFINES"
    },
    {
      "id": "67f18cd9-23d5-49ec-ae24-a38ddf66578e",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "4f908858-43ae-4e1f-8f5a-bbbb1e4cdc68",
      "type": "GOVERNS"
    },
    {
      "id": "518b3c68-9e63-4f5f-abe2-fa16a78292ec",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "7aec918d-406d-44b6-8606-a1849e22b2fa",
      "type": "GOVERNS"
    },
    {
      "id": "a5625016-950f-4d2d-9b37-444f8d81491d",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "d3ba1009-d477-4301-a0ac-99dd5111c643",
      "type": "GOVERNS"
    },
    {
      "id": "7e2ec683-00e6-4e26-a765-71345413c5b2",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "69529699-03c7-47b2-85f0-b56c675adada",
      "type": "GOVERNS"
    },
    {
      "id": "7b61ad5a-1d72-4155-b8ae-25f151dd449f",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "type": "GOVERNS"
    },
    {
      "id": "73228222-8a95-4e28-bfca-e27a9f486072",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "type": "GOVERNS"
    },
    {
      "id": "7e667b37-f581-4690-b3b3-e94e2a65f90f",
      "source": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "target": "d70a271c-6f86-4b05-a29d-ebb5a91581d8",
      "type": "GOVERNS"
    },
    {
      "id": "7b828fb7-95f1-44dc-ad69-0dd8632a9c6f",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "b5683673-efc4-427b-9b01-548cb9fa56ea",
      "type": "TESTS"
    },
    {
      "id": "4cfa1227-9887-4943-a489-ccd7445a6e0c",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "4f908858-43ae-4e1f-8f5a-bbbb1e4cdc68",
      "type": "TESTS"
    },
    {
      "id": "e4730bc2-6b1c-467f-a97a-1ac861a84339",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "7aec918d-406d-44b6-8606-a1849e22b2fa",
      "type": "TESTS"
    },
    {
      "id": "bd42fc0a-3350-42cb-ba8c-fa1e1f46fcb4",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "d3ba1009-d477-4301-a0ac-99dd5111c643",
      "type": "TESTS"
    },
    {
      "id": "f59eecbf-a0ad-428d-803f-9df8859b0eed",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "69529699-03c7-47b2-85f0-b56c675adada",
      "type": "TESTS"
    },
    {
      "id": "4bbd58a9-ffc0-4af1-a1c8-4f4051ef400c",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "e456ba54-eac5-4a19-a63e-2197a4586201",
      "type": "TESTS"
    },
    {
      "id": "cd31dd6d-ed90-4f5e-8394-3496e80a4430",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "d70a271c-6f86-4b05-a29d-ebb5a91581d8",
      "type": "TESTS"
    },
    {
      "id": "9abb0448-bc38-463e-8790-d6e40496fa74",
      "source": "cc8db649-d4ba-48e7-af18-be94b1c03b6b",
      "target": "8309970c-9a24-4939-91dd-2a10e858fcac",
      "type": "TESTS"
    }
  ]
}