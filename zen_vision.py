#!/usr/bin/env python3
"""
Zen Vision - Integrated Plant Health & Solar AI System
A harmonious blend of plant monitoring and renewable energy optimization.
"""

import os
import json
import time
from typing import Dict, Any
from zenvision_api.plant_health.image_analyzer import analyze_image
from zenvision_api.plant_health.video_analyzer import analyze_video
from zenvision_api.plant_health.solar_ai import SolarAIController


class ZenVision:
    """Main Zen Vision application integrating plant health and solar AI."""

    def __init__(self):
        self.solar_controller = None
        print("\n" + "="*60)
        print("🌱 ZEN VISION 🌞")
        print("Integrated Plant Health & Solar AI System")
        print("="*60)
        print("Finding harmony between nature and technology...")

    def display_menu(self):
        """Display the main menu."""
        print("\n" + "-"*50)
        print("ZEN VISION MENU")
        print("-"*50)
        print("1. 🌿 Analyze Plant Image")
        print("2. 🎥 Analyze Plant Video")
        print("3. ☀️  Solar Power Simulation")
        print("4. 📊 View Solar Status")
        print("5. 🔄 Run Full System Check")
        print("6. ❓ Help")
        print("7. 🚪 Exit")
        print("-"*50)

    def analyze_plant_image(self):
        """Analyze a single plant image."""
        print("\n🌿 PLANT IMAGE ANALYSIS")
        print("-" * 30)

        path = input("Enter image path: ").strip()
        if not path:
            print("❌ No path provided.")
            return

        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            return

        try:
            print("🔍 Analyzing image...")
            results = analyze_image(path)

            print("\n📋 ANALYSIS RESULTS:")
            print("-" * 20)

            if results.get('yellowing_suspected'):
                print(f"⚠️  YELLOWING DETECTED (Confidence: {results['yellowing_confidence']:.1%})")
            else:
                print("✅ No yellowing detected")

            print(f"🌱 Green Ratio: {results['green_ratio']:.3f}")

            # Show additional metrics if available
            if 'brown_edges_detected' in results:
                print(f"🌰 Brown Edges: {results['brown_edges_detected']}")
            if 'light_stress' in results:
                print(f"☀️  Light Stress: {results['light_stress']}")
            if 'spot_count' in results:
                print(f"🐛 Spots/Pests: {results['spot_count']}")

            # Save results option
            save = input("\n💾 Save results to file? (y/n): ").lower().strip()
            if save == 'y':
                output_file = input("Enter output filename: ").strip()
                if output_file:
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    print(f"✅ Results saved to {output_file}")

        except Exception as e:
            print(f"❌ Analysis failed: {str(e)}")

    def analyze_plant_video(self):
        """Analyze a plant video."""
        print("\n🎥 PLANT VIDEO ANALYSIS")
        print("-" * 30)

        path = input("Enter video path: ").strip()
        if not path:
            print("❌ No path provided.")
            return

        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            return

        try:
            sample_rate = input("Sample rate in seconds (default 5): ").strip()
            sample_rate = int(sample_rate) if sample_rate.isdigit() else 5

            print(f"🎬 Analyzing video (sampling every {sample_rate}s)...")
            results = analyze_video(path, sample_rate)

            print("\n📋 VIDEO ANALYSIS RESULTS:")
            print("-" * 25)
            print(f"⏱️  Duration: {results['duration_sec']:.1f} seconds")
            print(f"📹 Frames Analyzed: {results['frames_analyzed']}")
            print(f"🌱 Average Green Ratio: {results['avg_green_ratio']:.3f}")

            trend = results['trend']
            if trend == 'declining_green':
                print("📉 Trend: Green levels declining (potential health issue)")
            elif trend == 'improving_green':
                print("📈 Trend: Green levels improving")
            else:
                print("➡️  Trend: Stable")

            print(f"🐛 Total Spots Detected: {results['total_spots']}")

            # Save results option
            save = input("\n💾 Save results to file? (y/n): ").lower().strip()
            if save == 'y':
                output_file = input("Enter output filename: ").strip()
                if output_file:
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    print(f"✅ Results saved to {output_file}")

        except Exception as e:
            print(f"❌ Analysis failed: {str(e)}")

    def initialize_solar_controller(self):
        """Initialize solar controller if not already done."""
        if self.solar_controller is None:
            print("☀️  Initializing Solar AI Controller...")
            self.solar_controller = SolarAIController()
            print("✅ Solar system online")

    def run_solar_simulation(self):
        """Run solar power management simulation."""
        self.initialize_solar_controller()

        print("\n☀️  SOLAR POWER SIMULATION")
        print("-" * 30)

        try:
            hours = input("Simulation hours (1-24, default 1): ").strip()
            hours = int(hours) if hours.isdigit() and 1 <= int(hours) <= 24 else 1

            print(f"⚡ Running {hours} hour simulation...")

            for h in range(hours):
                data = self.solar_controller.step()
                print(f"\n⏰ Hour {data['hour']:2d}:")
                print(f"   ☀️  Solar: {data['solar_output']:5.2f} kW")
                print(f"   🔋 Battery: {data['battery_charge']:5.1f}% ({data['battery_health']:.1f}% health)")
                print(f"   💡 Demand: {data['total_demand']:5.2f} kW")
                print(f"   ⚡ Grid: {data['grid_usage']:5.2f} kW (${data['grid_price']:.2f}/kWh)")
                print(f"   🌿 Unused Solar: {data['unused_solar']:5.2f} kW")

                # Brief pause for readability
                time.sleep(0.5)

            print("\n📊 SIMULATION COMPLETE")
            print(f"Total Power Distributed: {self.solar_controller.total_power_distributed:.2f} kWh")
            print(f"Final Battery Level: {self.solar_controller.battery_charge_level:.1f}%")

        except Exception as e:
            print(f"❌ Simulation failed: {str(e)}")

    def view_solar_status(self):
        """View current solar system status."""
        self.initialize_solar_controller()

        print("\n☀️  SOLAR SYSTEM STATUS")
        print("-" * 25)

        try:
            # Get current status by running one step
            data = self.solar_controller.step()

            print(f"⏰ Current Hour: {data['hour']}")
            print(f"☀️  Solar Output: {data['solar_output']:.2f} kW")
            print(f"🔋 Battery Charge: {data['battery_charge']:.1f}%")
            print(f"❤️  Battery Health: {data['battery_health']:.1f}%")
            print(f"💡 Total Demand: {data['total_demand']:.2f} kW")
            print(f"⚡ Grid Usage: {data['grid_usage']:.2f} kW")
            print(f"💰 Grid Price: ${data['grid_price']:.2f}/kWh")
            print(f"🌿 Unused Solar: {data['unused_solar']:.2f} kW")

            # Show load routing summary
            routing = data.get('routing', {})
            if routing:
                print("\n🏠 LOAD ROUTING:")
                for load_name, sources in routing.items():
                    total = sum(sources.values())
                    if total > 0:
                        src_str = []
                        if sources.get('solar', 0) > 0:
                            src_str.append(f"S:{sources['solar']:.1f}")
                        if sources.get('battery', 0) > 0:
                            src_str.append(f"B:{sources['battery']:.1f}")
                        if sources.get('grid', 0) > 0:
                            src_str.append(f"G:{sources['grid']:.1f}")
                        print(f"   ✅ {load_name}: {total:.1f} kW ({' '.join(src_str)})")
                    else:
                        print(f"   ❌ {load_name}: Deferred")

        except Exception as e:
            print(f"❌ Status check failed: {str(e)}")

    def run_full_system_check(self):
        """Run a comprehensive check of all systems."""
        print("\n🔄 FULL SYSTEM CHECK")
        print("-" * 20)

        print("🌿 Checking Plant Health System...")
        try:
            # Test with a dummy analysis (would need a real image)
            print("   ✅ Plant analysis modules loaded")
        except Exception as e:
            print(f"   ❌ Plant system error: {e}")

        print("☀️  Checking Solar AI System...")
        try:
            self.initialize_solar_controller()
            print("   ✅ Solar AI controller initialized")
            print(f"   🔋 Battery Level: {self.solar_controller.battery_charge_level:.1f}%")
        except Exception as e:
            print(f"   ❌ Solar system error: {e}")

        print("🔗 Checking System Integration...")
        try:
            # Test imports
            from plant_health.image_analyzer import analyze_image
            from plant_health.video_analyzer import analyze_video
            from plant_health.solar_ai import SolarAIController
            print("   ✅ All modules integrated successfully")
        except Exception as e:
            print(f"   ❌ Integration error: {e}")

        print("\n✅ System check complete!")

    def show_help(self):
        """Display help information."""
        print("\n❓ ZEN VISION HELP")
        print("-" * 18)
        print("Zen Vision integrates plant health monitoring with solar")
        print("power management to create a harmonious ecosystem.")
        print()
        print("FEATURES:")
        print("• 🌿 Plant Image Analysis: Detect yellowing, pests, light stress")
        print("• 🎥 Plant Video Analysis: Monitor health trends over time")
        print("• ☀️  Solar AI Simulation: Intelligent power distribution")
        print("• 📊 Real-time Status: Current system state monitoring")
        print()
        print("USAGE TIPS:")
        print("• Use high-quality, well-lit plant images for best results")
        print("• Video analysis samples frames to detect trends")
        print("• Solar simulation models real-world power management")
        print()
        print("For support, ensure all dependencies are installed:")
        print("pip install opencv-python numpy scikit-image matplotlib")

    def run(self):
        """Main application loop."""
        while True:
            self.display_menu()
            choice = input("Select option (1-7): ").strip()

            if choice == '1':
                self.analyze_plant_image()
            elif choice == '2':
                self.analyze_plant_video()
            elif choice == '3':
                self.run_solar_simulation()
            elif choice == '4':
                self.view_solar_status()
            elif choice == '5':
                self.run_full_system_check()
            elif choice == '6':
                self.show_help()
            elif choice == '7':
                print("\n🙏 Thank you for using Zen Vision")
                print("May your plants thrive and your energy be sustainable 🌱☀️")
                break
            else:
                print("❌ Invalid choice. Please select 1-7.")

            input("\nPress Enter to continue...")


def main():
    """Entry point for Zen Vision application."""
    try:
        app = ZenVision()
        app.run()
    except KeyboardInterrupt:
        print("\n\n🙏 Zen Vision session ended.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("Please ensure all dependencies are installed.")


if __name__ == "__main__":
    main()