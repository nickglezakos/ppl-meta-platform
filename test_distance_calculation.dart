// Test distance calculation for PPL Meta distance-based color coding
void main() {
  print('🧪 Testing Distance Calculation Function:');
  print('');
  
  // Test case 1: Large face (close distance)
  final largeArea = 65536.0; // 256x256 face
  final distance1 = calculateDistanceFromArea(largeArea);
  print('Large face (65,536px): ${distance1.toStringAsFixed(2)}m');
  
  // Test case 2: Medium face 
  final mediumArea = 47089.0; // From our backend test data
  final distance2 = calculateDistanceFromArea(mediumArea);
  print('Medium face (47,089px): ${distance2.toStringAsFixed(2)}m');
  
  // Test case 3: Small face (far distance)
  final smallArea = 10000.0; // 100x100 face
  final distance3 = calculateDistanceFromArea(smallArea);
  print('Small face (10,000px): ${distance3.toStringAsFixed(2)}m');
  
  print('');
  print('✅ Distance calculation test completed!');
  
  print('');
  print('🎨 Color Coding Results:');
  print('Large face → ${getColorName(distance1)}');
  print('Medium face → ${getColorName(distance2)}');
  print('Small face → ${getColorName(distance3)}');
}

// Test distance calculation
double calculateDistanceFromArea(double faceArea) {
  const double baselineFaceSize = 1000000.0;
  const double baselineDistance = 1.0;
  if (faceArea <= 0) return 100.0;
  final distance = (baselineFaceSize / faceArea) * baselineDistance;
  return distance.clamp(0.5, 100.0);
}

// Color coding test
String getColorName(double distance) {
  if (distance < 10) return 'Red (Very Close)';
  if (distance < 20) return 'Orange (Close)';
  if (distance < 30) return 'Yellow (Medium)';
  if (distance < 50) return 'Green (Far)';
  return 'Blue (Very Far)';
}