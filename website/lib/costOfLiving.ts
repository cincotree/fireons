export interface CityCostOfLiving {
  id: string;
  name: string;
  monthlyExpense: number;
  region: string;
}

export interface Region {
  id: string;
  name: string;
}

export const REGIONS: Region[] = [
  { id: 'cities', name: 'Cities' },
  { id: 'hill-stations', name: 'Hill Stations' },
  { id: 'beach-coastal', name: 'Beach & Coastal' },
  { id: 'heritage-desert', name: 'Heritage & Desert' },
  { id: 'eastern-himalayas', name: 'Eastern Himalayas & Northeast' },
  { id: 'other', name: 'Rural / Village (Custom)' },
];

export const CITY_COST_OF_LIVING: CityCostOfLiving[] = [
  { id: 'goa', name: 'Goa', monthlyExpense: 55000, region: 'beach-coastal' },
  { id: 'pondicherry', name: 'Pondicherry', monthlyExpense: 40000, region: 'beach-coastal' },
  { id: 'varkala', name: 'Varkala', monthlyExpense: 38000, region: 'beach-coastal' },
  { id: 'visakhapatnam', name: 'Visakhapatnam', monthlyExpense: 42000, region: 'beach-coastal' },

  { id: 'shimla', name: 'Shimla', monthlyExpense: 40000, region: 'hill-stations' },
  { id: 'manali', name: 'Manali', monthlyExpense: 38000, region: 'hill-stations' },
  { id: 'kasauli', name: 'Kasauli', monthlyExpense: 38000, region: 'hill-stations' },
  { id: 'dharamshala', name: 'Dharamshala', monthlyExpense: 35000, region: 'hill-stations' },
  { id: 'mount-abu', name: 'Mount Abu', monthlyExpense: 35000, region: 'hill-stations' },
  { id: 'dehradun', name: 'Dehradun', monthlyExpense: 40000, region: 'hill-stations' },
  { id: 'mussoorie', name: 'Mussoorie', monthlyExpense: 40000, region: 'hill-stations' },
  { id: 'rishikesh', name: 'Rishikesh', monthlyExpense: 35000, region: 'hill-stations' },
  { id: 'nainital', name: 'Nainital', monthlyExpense: 38000, region: 'hill-stations' },
  { id: 'coorg', name: 'Coorg (Madikeri)', monthlyExpense: 38000, region: 'hill-stations' },
  { id: 'chikmagalur', name: 'Chikmagalur', monthlyExpense: 35000, region: 'hill-stations' },
  { id: 'ooty', name: 'Ooty', monthlyExpense: 38000, region: 'hill-stations' },
  { id: 'kodaikanal', name: 'Kodaikanal', monthlyExpense: 35000, region: 'hill-stations' },
  { id: 'munnar', name: 'Munnar', monthlyExpense: 35000, region: 'hill-stations' },
  { id: 'panchgani-mahabaleshwar', name: 'Panchgani / Mahabaleshwar', monthlyExpense: 38000, region: 'hill-stations' },

  { id: 'udaipur', name: 'Udaipur', monthlyExpense: 38000, region: 'heritage-desert' },
  { id: 'jaipur', name: 'Jaipur', monthlyExpense: 42000, region: 'heritage-desert' },
  { id: 'mysuru', name: 'Mysuru', monthlyExpense: 42000, region: 'heritage-desert' },

  { id: 'darjeeling', name: 'Darjeeling', monthlyExpense: 35000, region: 'eastern-himalayas' },
  { id: 'gangtok', name: 'Gangtok', monthlyExpense: 35000, region: 'eastern-himalayas' },
  { id: 'shillong', name: 'Shillong', monthlyExpense: 35000, region: 'eastern-himalayas' },

  { id: 'pune', name: 'Pune', monthlyExpense: 60000, region: 'cities' },
  { id: 'coimbatore', name: 'Coimbatore', monthlyExpense: 45000, region: 'cities' },
  { id: 'chandigarh', name: 'Chandigarh', monthlyExpense: 55000, region: 'cities' },

  { id: 'other', name: 'Unlisted village / custom', monthlyExpense: 30000, region: 'other' },
];

export function citiesByRegion(regionId: string): CityCostOfLiving[] {
  return CITY_COST_OF_LIVING.filter((city) => city.region === regionId);
}

export function findCityById(cityId: string): CityCostOfLiving | undefined {
  return CITY_COST_OF_LIVING.find((city) => city.id === cityId);
}

export const isValidCityId = (value: string): boolean => CITY_COST_OF_LIVING.some((city) => city.id === value);

export const isValidRegionId = (value: string): boolean => REGIONS.some((region) => region.id === value);
