<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');
header('Access-Control-Allow-Headers: Content-Type');

// Function to map numeric status to CSS class
function mapStatus($statusCode) {
    $code = intval($statusCode);
    if ($code == 0) return 'ok';
    if ($code == 1 || $code == 2) return 'warn';
    if ($code == 3) return 'critical';
    if ($code == 4) return 'stale';
    return 'unknown';
}

// Function to read CSV file
function readCSV($filename) {
    $data = [];
    if (($handle = fopen($filename, 'r')) !== false) {
        $headers = fgetcsv($handle);
        while (($row = fgetcsv($handle)) !== false) {
            $data[] = array_combine($headers, $row);
        }
        fclose($handle);
    }
    return $data;
}

// Load CSV files
$inventory = readCSV('DCP_Inventory_R1.csv');
$status = readCSV('DCP_Status.csv');

// Create associative array for status data by DCP Name
$statusMap = [];
foreach ($status as $row) {
    $statusMap[$row['DCP Name']] = $row;
}

// Merge data and organize
$groupedData = [];
$listData = [];

foreach ($inventory as $row) {
    $process = trim($row['Process']);
    $desc = $row['Description'];
    $lineNo = trim($row['Line_no']);
    
    // Determine section
    $section = null;
    $isListSection = false;
    
    if (in_array($process, ['ALHSA', 'NLHSA'])) {
        $section = 'hsa';
    } elseif (in_array($process, ['ALDA', 'NLDA'])) {
        $section = 'disassy';
    } elseif (in_array($process, ['ALHDA', 'NLHDA'])) {
        $section = 'hda';
    } elseif ($process == 'WCS') {
        $section = 'wcs';
        $isListSection = true;
    } elseif ($process == 'STW') {
        if (strpos($desc, 'AOI') !== false) {
            $section = 'aoi';
            $isListSection = true;
        } else {
            $section = 'smachine';
            $isListSection = true;
        }
    }
    
    if (!$section) continue;
    
    // Get status data
    $dcpName = $row['DCP Name'];
    $statusData = isset($statusMap[$dcpName]) ? $statusMap[$dcpName] : [];
    
    $statusCode = isset($statusData['Status']) ? intval($statusData['Status']) : 0;
    
    // Create data object
    $data = [
        'id' => $dcpName,
        'desc' => $desc,
        'loc' => $row['Location_Code'],
        'status' => mapStatus($statusCode),
        'status_code' => $statusCode,
        'stop' => isset($statusData['Stop_Cnt']) ? intval($statusData['Stop_Cnt']) : 0,
        'l1' => isset($statusData['Check_L1_Cnt']) ? intval($statusData['Check_L1_Cnt']) : 0,
        'l2' => isset($statusData['Check_L2_Cnt']) ? intval($statusData['Check_L2_Cnt']) : 0,
        'average' => isset($statusData['Average']) ? floatval($statusData['Average']) : 0,
        'line_no' => $lineNo
    ];
    
    if ($isListSection) {
        $listData[$section][] = $data;
    } else {
        if (!isset($groupedData[$section])) {
            $groupedData[$section] = [];
        }
        if (!isset($groupedData[$section][$lineNo])) {
            $groupedData[$section][$lineNo] = [];
        }
        $groupedData[$section][$lineNo][] = $data;
    }
}

// Flatten grouped data
$sensorMap = [];

foreach ($groupedData as $section => $lines) {
    foreach ($lines as $lineNo => $items) {
        foreach ($items as $idx => $item) {
            $key = $section . '-' . $lineNo . '-' . $idx;
            $sensorMap[$key] = $item;
        }
    }
}

// Add list sections
foreach ($listData as $section => $items) {
    $sensorMap[$section] = $items;
}

// Return JSON
echo json_encode($sensorMap);
?>