<!DOCTYPE html>
<html>
<head>
<title>VM Inventory</title>
<style>
table, th, td {
  border: 1px solid grey;
  border-collapse:collapse;
}
th, td {
  padding: 5px;
}
th {
  background-color: #ff6600;
  color: white;
}
tr:nth-child(even) {
  background-color: #e6e6e6;
}
tr:nth-child(odd) {
  background-color: #cccccc;
}
</style>
</head>
<body bgcolor=#F0F8FF>

<?php
$hostlist = "hostlist.txt";
$array = file($hostlist, FILE_IGNORE_NEW_LINES);
foreach ($array as $file){
  $xml = simplexml_load_file("xml/" . $file . ".xml");
  echo "<strong>" . $file . "</strong>" . " - last update: " . date ("F d Y H:i:s", filemtime("xml/" . $file . ".xml")) . " - " . "<a href=" . $xml->hypervisor . " target=" . "_blank" . ">Console</a>";
  echo "<table style='width:100%'>";
  echo "<tr>";
  echo "<th width='2%'>Vmid</th>";
  echo "<th width='8%'>Name</th>";
  echo "<th width='5%'>IpAddress</th>";
  echo "<th width='12%'>Hostname</th>";
  echo "<th width='20%'>GuestOS</th>";
  echo "<th width='10%'>Owner</th>";
  echo "<th width='10%'>Team</th>";
  echo "<th width='23%'>Description</th>";
  echo "<th width='10%'>ExpiryDate</th>";
  echo "</tr>";
  foreach($xml->vm as $vm){
    echo "<tr>";
    echo "<td>{$vm->vmid}</td>";
    echo "<td>{$vm->name}</td>";
    echo "<td>{$vm->ipaddress}</td>";
    echo "<td>{$vm->hostname}</td>";
    echo "<td>{$vm->guestos}</td>";
    echo "<td>{$vm->owner}</td>";
    echo "<td>{$vm->team}</td>";
    echo "<td>{$vm->description}</td>";
    echo "<td>{$vm->expirydate}</td>";
    echo "</tr>";
  }
echo "</table>";
echo "<br></br>";
}
?>

</body>
</html>
