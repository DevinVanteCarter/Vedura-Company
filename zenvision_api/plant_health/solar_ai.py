 #!/usr/bin/env python3
"""
Solar Grid AI Power Management System
Intelligently reroutes power between solar, battery, and grid sources.
"""

import random
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class PowerSource:
    """Represents a power source in the grid."""
    name: str
    capacity: float  # kWh
    current_output: float  # kW
    efficiency: float  # 0-1
    
    def get_available_power(self) -> float:
        """Get currently available power output."""
        return self.current_output * self.efficiency

@dataclass
class LoadDemand:
    """Represents a power load/demand."""
    name: str
    required_power: float  # kW
    priority: int  # 1-10, higher = more critical
    is_essential: bool
    
class SolarAIController:
    """AI controller for intelligent solar grid power management."""
    
    def __init__(self):
        self.solar_panel = PowerSource("Solar Panel", 50.0, 0.0, 0.95)
        self.battery_bank = PowerSource("Battery Bank", 100.0, 0.0, 0.90)
        self.grid_connection = PowerSource("Grid Connection", 1000.0, 0.0, 0.98)
        
        self.loads: List[LoadDemand] = [
            LoadDemand("Home Base", 5.0, 10, is_essential=True),
            LoadDemand("HVAC System", 3.5, 8, is_essential=True),
            LoadDemand("Water Pump", 2.0, 7, is_essential=True),
            LoadDemand("Computing Cluster", 4.0, 6, is_essential=False),
            LoadDemand("Charging Station", 2.5, 3, is_essential=False),
        ]
        
        self.battery_charge_level = 40.0  # % of capacity
        self.grid_demand_price = 1.5  # $/kWh - grid is expensive backup
        self.total_power_distributed = 0.0
        self.simulation_hour = 0
    
    def _simulate_solar_output(self) -> float:
        """Simulate solar panel output based on time of day."""
        hour = self.simulation_hour % 24
        
        # Peak output at noon (hour 12)
        if hour < 6 or hour > 18:
            output = 0.0  # Night
        elif hour < 12:
            output = (hour - 6) * 3.5  # Morning ramp
        else:
            output = (18 - hour) * 3.5  # Evening ramp
        
        # Add some randomness (clouds, etc.)
        output += random.uniform(-2, 2)
        return max(0, output)
    
    def _calculate_battery_health(self) -> float:
        """Calculate battery health based on charge cycles and level."""
        base_health = 100.0
        
        # Health degrades over time
        health = base_health - (self.simulation_hour * 0.01)
        
        # Lower health when overcharged or undercharged
        if self.battery_charge_level > 90:
            health -= 5
        elif self.battery_charge_level < 10:
            health -= 10
        
        return max(0, health)
    
    def _prioritize_loads(self) -> List[LoadDemand]:
        """Sort loads by priority and essentiality."""
        return sorted(
            self.loads,
            key=lambda x: (not x.is_essential, -x.priority)
        )
    
    def _calculate_optimal_routing(self) -> Dict[str, float]:
        """
        AI algorithm to determine optimal power routing.
        Considers: solar availability, battery level, grid cost, load priority.
        """
        # Return detailed per-load source breakdown: {load: {'solar':x,'battery':y,'grid':z}}
        routing: Dict[str, Dict[str, float]] = {load.name: {'solar': 0.0, 'battery': 0.0, 'grid': 0.0} for load in self.loads}

        solar_available = self.solar_panel.get_available_power()
        battery_available = (self.battery_charge_level / 100.0) * self.battery_bank.capacity

        # Prioritized loads should be served first
        prioritized_loads = self._prioritize_loads()

        remaining_solar = solar_available
        remaining_battery = battery_available
        grid_usage = 0.0

        for load in prioritized_loads:
            need = load.required_power
            # Essential loads: use solar first, then battery, then grid
            if load.is_essential:
                use_solar = min(remaining_solar, need)
                routing[load.name]['solar'] = use_solar
                remaining_solar -= use_solar
                need -= use_solar

                if need > 0:
                    use_batt = min(remaining_battery, need)
                    routing[load.name]['battery'] = use_batt
                    remaining_battery -= use_batt
                    need -= use_batt

                if need > 0:
                    routing[load.name]['grid'] = need
                    grid_usage += need
            else:
                # Non-essential: use excess solar first, then battery only if the system is healthy
                use_solar = min(remaining_solar, need)
                routing[load.name]['solar'] = use_solar
                remaining_solar -= use_solar
                need -= use_solar

                if need > 0 and remaining_battery > (0.25 * self.battery_bank.capacity):
                    use_batt = min(remaining_battery, need)
                    routing[load.name]['battery'] = use_batt
                    remaining_battery -= use_batt
                    need -= use_batt

                # Non-essential load only takes grid power as a last-resort backup
                if need > 0 and self.grid_demand_price < 0.6:
                    routing[load.name]['grid'] = need
                    grid_usage += need
                else:
                    # defer non-essential when grid is expensive or battery is reserved
                    pass

        return routing
    
    def _update_battery_level(self, solar_output: float, total_demand: float):
        """Update battery charge level based on energy flow."""
        excess_solar = solar_output - total_demand
        
        if excess_solar > 0:
            # Charge battery with excess solar, accounting for efficiency
            charge_increase = (excess_solar * self.battery_bank.efficiency / self.battery_bank.capacity) * 100
            self.battery_charge_level = min(100.0, self.battery_charge_level + charge_increase)
        else:
            # Discharge battery to cover the deficit before grid backup
            discharge = abs(excess_solar) / self.battery_bank.capacity * 100 / self.battery_bank.efficiency
            self.battery_charge_level = max(0.0, self.battery_charge_level - discharge)

    def reroute_decision(self) -> Dict:
        """Produce an explainable reroute decision based on current state.
        Returns per-load source breakdown and a list of actionable commands.
        """
        routing = self._calculate_optimal_routing()

        actions: List[str] = []
        for load_name, src in routing.items():
            s = src.get('solar', 0.0)
            b = src.get('battery', 0.0)
            g = src.get('grid', 0.0)
            parts = []
            if s > 0:
                parts.append(f"{s:.2f}kW from SOLAR")
            if b > 0:
                parts.append(f"{b:.2f}kW from BATTERY")
            if g > 0:
                parts.append(f"{g:.2f}kW from GRID")
            if parts:
                actions.append(f"Route to {load_name}: " + ", ".join(parts))
            else:
                actions.append(f"Defer {load_name} (no supply assigned)")

        # High-level recommendations
        if self.battery_charge_level < 20:
            actions.append("Recommendation: Prioritize charging battery during next high-solar period.")
        if self.grid_demand_price > 0.8:
            actions.append("Recommendation: Minimize grid draw; enable demand response if available.")

        return {'routing': routing, 'actions': actions, 'battery_charge': round(self.battery_charge_level,1), 'grid_price': round(self.grid_demand_price,2)}
    
    def step(self) -> Dict:
        """Execute one simulation step (1 hour)."""
        # Update environmental factors
        solar_output = self._simulate_solar_output()
        self.solar_panel.current_output = solar_output
        
        # Calculate optimal power routing
        routing = self._calculate_optimal_routing()
        # routing now contains per-load source dicts
        total_demand = sum(sum(s.values()) for s in routing.values())
        
        # Update battery level
        self._update_battery_level(solar_output, total_demand)
        
# Simulate grid demand pricing for backup use only
        self.grid_demand_price = 1.2 + random.uniform(-0.1, 0.2)
        
        # Calculate metrics
        battery_health = self._calculate_battery_health()
        unused_solar = max(0, solar_output - total_demand)
        
        self.total_power_distributed += total_demand
        self.simulation_hour += 1
        
        return {
            "hour": self.simulation_hour,
            "solar_output": round(solar_output, 2),
            "battery_charge": round(self.battery_charge_level, 1),
            "battery_health": round(battery_health, 1),
            "total_demand": round(total_demand, 2),
            "grid_usage": round(grid_usage, 2),
            "unused_solar": round(unused_solar, 2),
            "grid_price": round(self.grid_demand_price, 2),
            "routing": {k: {sk: round(sv, 2) for sk, sv in v.items()} for k, v in routing.items()}
        }
    
    def display_status(self, data: Dict):
        """Display formatted status report."""
        print("\n" + "="*70)
        print(f"SOLAR GRID AI - HOUR {data['hour']:03d}")
        print("="*70)
        print(f"Solar Output:        {data['solar_output']:6.2f} kW")
        print(f"Battery Charge:      {data['battery_charge']:6.1f}% (Health: {data['battery_health']:.1f}%)")
        print(f"Total Demand:        {data['total_demand']:6.2f} kW")
        print(f"Grid Usage:          {data['grid_usage']:6.2f} kW (${data['grid_price']:.2f}/kWh)")
        print(f"Unused Solar:        {data['unused_solar']:6.2f} kW")
        print("-"*70)
        print("LOAD ROUTING (sources):")
        for load_name, sources in data['routing'].items():
            total = sum(sources.values())
            status = "✓" if total > 0 else "✗"
            src_parts = []
            if sources.get('solar', 0) > 0:
                src_parts.append(f"S:{sources['solar']:.2f}kW")
            if sources.get('battery', 0) > 0:
                src_parts.append(f"B:{sources['battery']:.2f}kW")
            if sources.get('grid', 0) > 0:
                src_parts.append(f"G:{sources['grid']:.2f}kW")
            print(f"  {status} {load_name:20s}: {total:6.2f} kW [{' '.join(src_parts)}]")
        print("="*70)
    
    def run_simulation(self, hours: int = 24):
        """Run full simulation for specified hours."""
        print("\n" + "="*70)
        print("SOLAR GRID AI POWER MANAGEMENT SYSTEM")
        print(f"Initializing simulation for {hours} hours...")
        print("="*70)
        
        for _ in range(hours):
            data = self.step()
            self.display_status(data)
        
        # Final report
        print("\n" + "="*70)
        print("SIMULATION COMPLETE")
        print("="*70)
        print(f"Total Power Distributed: {self.total_power_distributed:.2f} kWh")
        print(f"Final Battery Level:     {self.battery_charge_level:.1f}%")
        print(f"Average Simulation:      {self.total_power_distributed/hours:.2f} kWh/hr")
        print("="*70 + "\n")

def main():
    """Main entry point."""
    controller = SolarAIController()
    controller.run_simulation(hours=24)

if __name__ == "__main__":
    main()
