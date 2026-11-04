// Sprint 3, US30/US31/US32 — Azure deployment template (NOT provisioned).
// This file is infrastructure-as-code for review/demo only. Provisioning
// it would create paid Azure resources, so it is NOT run in CI and NOT
// run without Vin's explicit approval of the specific deployment.
// Resources match docs/architecture.md: VMSS (min 2) + Load Balancer +
// Azure Database for PostgreSQL + Blob Storage + Key Vault + App Insights.
// Secrets: never in this file — Key Vault references only.
param location string = resourceGroup().location
param adminPassword string // @secure() in a real deployment; passed via Key Vault, never committed
param vmssInstanceCount int = 2

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: 'staynest-vnet'
  location: location
  properties: { addressSpace: { addressPrefixes: ['10.0.0.0/16'] } }
}
resource lb 'Microsoft.Network/loadBalancers@2023-05-01' = {
  name: 'staynest-lb'
  location: location
  properties: {
    frontendIPConfigurations: [{ name: 'frontend', properties: { publicIPAddress: { id: publicIp.id } } }]
    backendAddressPools: [{ name: 'backend' }]
    loadBalancingRules: [{ name: 'api', properties: { frontendIPConfiguration: { id: resourceId('Microsoft.Network/loadBalancers/frontendIPConfigurations', 'staynest-lb', 'frontend') }, backendAddressPool: { id: resourceId('Microsoft.Network/loadBalancers/backendAddressPools', 'staynest-lb', 'backend') }, protocol: 'Tcp', frontendPort: 80, backendPort: 8000 } }]
  }
}
resource publicIp 'Microsoft.Network/publicIPAddresses@2023-05-01' = {
  name: 'staynest-ip'
  location: location
  properties: { publicIPAllocationMethod: 'Static' }
}
resource vmss 'Microsoft.Compute/virtualMachineScaleSets@2023-09-01' = {
  name: 'staynest-vmss'
  location: location
  sku: { name: 'Standard_B2s', capacity: vmssInstanceCount }
  properties: {
    overprovision: false
    upgradePolicy: { mode: 'Rolling' }
    virtualMachineProfile: {
      osProfile: { computerNamePrefix: 'staynest', adminUsername: 'staynest', adminPassword: adminPassword }
      storageProfile: { imageReference: { publisher: 'Canonical', offer: '0001-com-ubuntu-server-jammy', sku: '22_04-lts', version: 'latest' } }
      networkProfile: { networkInterfaceConfigurations: [{ name: 'nic', properties: { primary: true, ipConfigurations: [{ name: 'ip', properties: { subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', 'staynest-vnet', 'default') }, loadBalancerBackendAddressPools: [{ id: resourceId('Microsoft.Network/loadBalancers/backendAddressPools', 'staynest-lb', 'backend') }] } }] } }] }
    }
  }
}
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: 'staynest-db'
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: { version: '16', administratorLogin: 'staynest', administratorLoginPassword: adminPassword, storage: { storageSizeGB: 32 } }
}
resource blob 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'staynestblob'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'staynest-vault'
  location: location
  properties: { tenantId: subscription().tenantId, sku: { family: 'A', name: 'standard' }, enableSoftDelete: true }
}
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'staynest-insights'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web' }
}
output lbIp string = publicIp.properties.ipAddress
