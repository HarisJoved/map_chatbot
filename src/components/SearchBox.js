import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import { LocationService } from '../services/locationService';

const SearchContainer = styled.div`
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 5;
  width: 300px;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 12px 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  font-size: 16px;
  outline: none;
  background-color: #fff;
  &:focus {
    border-color: #01a3a4;
    box-shadow: 0 2px 8px rgba(1, 163, 164, 0.3);
  }
`;

const SearchResults = styled.div`
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  margin-top: 5px;
  max-height: 300px;
  overflow-y: auto;
  display: ${props => props.show ? 'block' : 'none'};
`;

const SearchResultItem = styled.div`
  padding: 10px 15px;
  cursor: pointer;
  border-bottom: 1px solid #f1f1f1;
  &:hover {
    background-color: #f9f9f9;
  }
  &:last-child {
    border-bottom: none;
  }
`;

const Address = styled.div`
  font-weight: bold;
  color: #222;
`;
const Postcode = styled.div`
  font-size: 0.95em;
  color: #666;
`;

const LoadingIndicator = styled.div`
  text-align: center;
  padding: 10px;
  color: #666;
  font-style: italic;
`;

const NoResults = styled.div`
  text-align: center;
  padding: 10px;
  color: #666;
  font-style: italic;
`;

const SearchBox = ({ onSearch }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [debouncedTerm, setDebouncedTerm] = useState("");

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Perform search when debounced term changes
  useEffect(() => {
    const performSearch = async () => {
      if (!debouncedTerm.trim()) {
        setResults([]);
        setShowResults(false);
        return;
      }

      setIsLoading(true);
      try {
        const searchResults = await LocationService.searchLocations(debouncedTerm);
        setResults(searchResults);
        setShowResults(true);
      } catch (error) {
        console.error("Error searching locations:", error);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    };

    performSearch();
  }, [debouncedTerm]);

  const handleSearch = (e) => {
    const term = e.target.value;
    setSearchTerm(term);
  };

  const handleSelectLocation = (location) => {
    setSearchTerm(location.address + (location.postcode ? `, ${location.postcode}` : ''));
    setShowResults(false);
    onSearch(location);
  };

  const handleClickOutside = useCallback((e) => {
    if (!e.target.closest('.search-container')) {
      setShowResults(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [handleClickOutside]);

  return (
    <SearchContainer className="search-container">
      <SearchInput
        type="text"
        placeholder="Search by address or postcode"
        value={searchTerm}
        onChange={handleSearch}
        onFocus={() => searchTerm.trim() && setShowResults(true)}
      />
      
      <SearchResults show={showResults && (results.length > 0 || isLoading)}>
        {isLoading ? (
          <LoadingIndicator>Searching...</LoadingIndicator>
        ) : results.length > 0 ? (
          results.map(location => (
            <SearchResultItem 
              key={location.address + location.postcode}
              onClick={() => handleSelectLocation(location)}
            >
              <Address>{location.address}</Address>
              <Postcode>{location.postcode}</Postcode>
            </SearchResultItem>
          ))
        ) : (
          <NoResults>No locations found</NoResults>
        )}
      </SearchResults>
    </SearchContainer>
  );
};

export default SearchBox; 